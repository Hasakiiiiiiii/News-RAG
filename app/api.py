from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import time
import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from typing import List, Optional, Any


# Load biến môi trường
load_dotenv()

# Import core components
from search.engine import Pipeline
from search.generator import generator_registry
from search.retriever import Retriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="News RAG Search API (PostgreSQL & Multi-Test)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE CONNECTION ---
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "postgres"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            port=os.getenv("DB_PORT", "5432")
        )
        return conn
    except Exception as e:
        logger.error(f"Lỗi kết nối PostgreSQL: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# --- SINGLETONS ---
pipeline = None
retriever_instance = None

def get_pipeline():
    global pipeline
    if pipeline is None:
        logger.info("[*] Initializing Pipeline...")
        pipeline = Pipeline()
    return pipeline

def get_retriever():
    global retriever_instance
    if retriever_instance is None:
        logger.info("[*] Initializing pure Retriever...")
        retriever_instance = Retriever()
    return retriever_instance

# --- SCHEMAS ---
class SearchRequest(BaseModel):
    query: str
    model: Optional[str] = "default"

# --- CORE ROUTES ---

@app.post("/search")
async def search(request: SearchRequest):
    """(Từ file run_e2e_test & interactive_test): Chạy Full RAG Pipeline"""
    p = get_pipeline()
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query is required")

    try:
        response = p.ask(request.query.strip(), model=request.model)
        
        separator = "-" * 30
        results_list = getattr(response, 'results', []) or []
        ref_list = [f"[{i+1}] {hit.title} | Link: {hit.url}" for i, hit in enumerate(results_list)]
        references_section = "\n\nReferences Used:\n" + "\n".join(ref_list) if ref_list else ""
        
        summary = response.summary if response else "Không tìm thấy câu trả lời."
        total = getattr(response, 'total', 0)
        duration = getattr(response, 'duration_ms', 0)

        formatted_output = (
            f"{separator}\n AI trả lời:\n{summary}\n\n"
            f"Thông tin: {total} nguồn tin | Thời gian: {duration}ms"
            f"{references_section}\n{separator}"
        )

        return {
            "raw_data": {
                "summary": summary,
                "results": results_list,
                "total": total,
                "duration_ms": duration
            }, 
            "formatted_answer": formatted_output
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/retrieve")
async def retrieve_only(request: SearchRequest):
    """(Từ file run_real_search): Test hệ thống tìm kiếm thuần túy trên Qdrant Cloud"""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query is required")
        
    try:
        r = get_retriever()
        results = r.search(request.query.strip())
        
        if not results:
            return {"message": "Không tìm thấy kết quả từ Qdrant.", "results": []}
            
        formatted_results = []
        for hit in results:
            formatted_results.append({
                "title": hit.title,
                "url": hit.url,
                "score": round(hit.score, 4),
                "content_snippet": hit.content[:250] + "..." # Cắt ngắn để dễ nhìn
            })
            
        return {
            "query": request.query,
            "total_found": len(formatted_results),
            "results": formatted_results
        }
    except Exception as e:
        logger.error(f"Retrieve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/compare")
async def compare_all_models(request: SearchRequest):
    """(Từ file test_scaling_generators): Gửi câu hỏi đến TẤT CẢ model cùng lúc"""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query is required")

    try:
        r = get_retriever()
        query = request.query.strip()
        search_hits = r.search(query)
        
        if not search_hits:
            return {"message": "Không tìm thấy context từ database, bỏ qua gọi LLM."}

        available_models = generator_registry.list_generators()
        comparison_results = []

        for model_info in available_models:
            model_name = model_info.get("name")
            if not model_name:
                continue
                
            try:
                gen = generator_registry.get_generator(model_name)
                # Lưu ý: Code cũ generator trả về obj hay text phụ thuộc vào generator.generate()
                # Thường nó trả về một string hoặc object chứa answer
                response = gen.generate(query, search_hits)
                comparison_results.append({
                    "model": model_name,
                    "provider": model_info.get("provider", "unknown"),
                    "response": response
                })
            except Exception as model_err:
                comparison_results.append({
                    "model": model_name,
                    "error": str(model_err)
                })

        return {
            "query": query,
            "context_documents": len(search_hits),
            "model_responses": comparison_results
        }
    except Exception as e:
        logger.error(f"Compare error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- DATABASE REST ROUTES ---

@app.get("/sources")
async def list_sources():
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name, url, description FROM sources ORDER BY id")
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

@app.get("/articles")
async def list_articles(q: Optional[str] = None, limit: int = 10, offset: int = 0):
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Câu query chuẩn Data Warehouse: Kết nối Fact và các Dim
        base_query = """
            SELECT 
                f.article_id AS id, 
                f.title, 
                m.url, 
                s.domain AS source,
                t.date AS published_date,
                STRING_AGG(a.author_name, ' & ') AS author,
                MAX(SUBSTRING(c.content, 1, 150)) || '...' AS snippet
            FROM fact_articles f
            LEFT JOIN dim_source s ON f.source_id = s.source_id
            LEFT JOIN dim_time t ON f.time_id = t.time_id
            LEFT JOIN fact_article_authors faa ON f.article_id = faa.article_id
            LEFT JOIN dim_author a ON faa.author_id = a.author_id
            LEFT JOIN dim_content c ON f.content_id = c.content_id
            LEFT JOIN article_metadata m ON f.url_hash = m.url_hash
        """

        if q and q.strip():
            search_term = f"%{q.strip()}%"
            query = base_query + """
                WHERE f.title ILIKE %s
                GROUP BY f.article_id, f.title, m.url, s.domain, t.date
                ORDER BY t.date DESC 
                LIMIT %s OFFSET %s
            """
            cur.execute(query, (search_term, limit, offset))
        else:
            query = base_query + """
                GROUP BY f.article_id, f.title, m.url, s.domain, t.date
                ORDER BY t.date DESC 
                LIMIT %s OFFSET %s
            """
            cur.execute(query, (limit, offset))
            
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

@app.get("/stats")
async def get_stats():
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Đếm Nguồn tin
        cur.execute("SELECT COUNT(*) as count FROM dim_source")
        s_count = cur.fetchone()['count']
        
        # 2. Đếm tổng số bài báo
        cur.execute("SELECT COUNT(*) as count FROM article_metadata")
        a_count = cur.fetchone()['count']

        # 3. Đếm tổng số Vector
        cur.execute("SELECT COUNT(*) as count FROM fact_chunks")
        v_count = cur.fetchone()['count']

        # 4. Lấy Top 5 Tác giả
        cur.execute("""
            SELECT a.author_name as name, COUNT(faa.article_id) as count
            FROM fact_article_authors faa
            JOIN dim_author a ON faa.author_id = a.author_id
            GROUP BY a.author_name
            ORDER BY count DESC
            LIMIT 5
        """)
        top_authors = cur.fetchall()

        if top_authors:
            max_count = top_authors[0]['count']
            for auth in top_authors:
                auth['percent'] = int((auth['count'] / max_count) * 100) if max_count > 0 else 0

        # 5. Lấy phân bổ nguồn tin cho Pie Chart (THÊM MỚI Ở ĐÂY)
        cur.execute("""
            SELECT s.domain as name, COUNT(f.article_id) as value
            FROM fact_articles f
            JOIN dim_source s ON f.source_id = s.source_id
            GROUP BY s.domain
            ORDER BY value DESC
        """)
        source_distribution = cur.fetchall()

        # Tính phần trăm % cho từng nguồn báo
        total_pie_articles = sum(item['value'] for item in source_distribution)
        for item in source_distribution:
            item['percent'] = round((item['value'] / total_pie_articles) * 100, 1) if total_pie_articles > 0 else 0

        # 6. Lấy dữ liệu trend (Line Chart) - Số bài theo ngày (7 ngày gần nhất có dữ liệu)
        cur.execute("""
            SELECT TO_CHAR(t.date, 'DD/MM') as date, COUNT(f.article_id) as count
            FROM fact_articles f
            JOIN dim_time t ON f.time_id = t.time_id
            WHERE t.date IS NOT NULL
            GROUP BY t.date
            ORDER BY t.date DESC
            LIMIT 7
        """)
        trend_data = cur.fetchall()
        # Đảo ngược mảng lại (từ cũ đến mới) để Line Chart vẽ từ trái qua phải cho đúng chiều thời gian
        trend_data.reverse()

        # 7. Lấy 5 bài báo mới nhất (Thay thế cho Keywords)
        cur.execute("""
            SELECT f.title, s.domain as source, TO_CHAR(t.date, 'DD/MM/YYYY') as date
            FROM fact_articles f
            JOIN dim_source s ON f.source_id = s.source_id
            JOIN dim_time t ON f.time_id = t.time_id
            ORDER BY f.article_id DESC
            LIMIT 10
        """)
        latest_articles = cur.fetchall()

        return {
            "total_sources": s_count, 
            "total_articles": a_count,
            "total_vectors": v_count,
            "top_authors": top_authors,
            "source_distribution": source_distribution,
            "trend_data": trend_data,
            "latest_articles": latest_articles # <-- Thêm dòng này
        }
    finally:
        cur.close()
        conn.close()
        
@app.get("/models")
async def list_models():
    return {"models": generator_registry.list_generators()}

@app.get("/health")
async def health_check():
    if pipeline is None or retriever_instance is None:
        return {"status": "initializing"}
    return {"status": "ok", "timestamp": int(time.time())}
# ==========================================
# --- TÍNH NĂNG MỚI: PIPELINE MONITORING ---
# ==========================================

@app.get("/monitor/metrics")
async def get_monitor_metrics():
    """Lấy các chỉ số tổng quan của kho dữ liệu (Data Warehouse)"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Bắt try-except phòng trường hợp bạn chưa chạy ETL tạo bảng fact_articles
        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM fact_articles) AS bai_bao,
                (SELECT COUNT(*) FROM fact_chunks) AS tong_chunks,
                (SELECT COUNT(*) FROM article_metadata WHERE publish_date = 'Unknown') AS loi_ngay
        """)
        data = cur.fetchone()
        
        bai_bao = data['bai_bao'] if data and data['bai_bao'] else 0
        chunks = data['tong_chunks'] if data and data['tong_chunks'] else 0
        loi_ngay = data['loi_ngay'] if data and data['loi_ngay'] else 0
        avg_chunks = round(chunks / bai_bao, 2) if bai_bao > 0 else 0

        return {
            "total_articles": bai_bao,
            "total_chunks": chunks,
            "avg_chunks_per_article": avg_chunks,
            "date_errors": loi_ngay
        }
    except Exception as e:
        logger.error(f"Lỗi Monitor Metrics: {e}")
        return {"error": "Bảng dữ liệu chưa sẵn sàng. Hãy chạy ETL trước!"}
    finally:
        cur.close()
        conn.close()

@app.get("/monitor/authors")
async def get_recent_authors():
    """Lấy danh sách 10 bài báo mới nhất và tác giả"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT f.title, STRING_AGG(a.author_name, ' & ') as authors 
            FROM fact_articles f 
            JOIN fact_article_authors faa ON f.article_id = faa.article_id 
            JOIN dim_author a ON faa.author_id = a.author_id 
            GROUP BY f.article_id, f.title 
            ORDER BY f.article_id DESC LIMIT 10;
        """)
        return cur.fetchall()
    except Exception as e:
        return []
    finally:
        cur.close()
        conn.close()

@app.get("/monitor/latest-chunks")
async def get_latest_chunks():
    """Lấy các chunks của bài báo mới nhất để kiểm tra thuật toán chia đoạn"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT chunk_index, content
            FROM fact_chunks 
            WHERE article_id = (SELECT MAX(article_id) FROM fact_articles) 
            ORDER BY chunk_index LIMIT 5;
        """)
        return cur.fetchall()
    except Exception as e:
        return []
    finally:
        cur.close()
        conn.close()
        
@app.get("/pipeline/status")
async def get_pipeline_status():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Kiểm tra số lượng tin nhắn chờ trong DB (giả sử bạn có bảng staging hoặc status)
        cur.execute("SELECT count(*) FROM fact_articles")
        total_articles = cur.fetchone()['count']
        
        # 2. Kiểm tra log ETL gần nhất (giả sử bạn có bảng log)
        # cur.execute("SELECT status, timestamp FROM etl_logs ORDER BY timestamp DESC LIMIT 5")
        # logs = cur.fetchall()

        return {
            "services": {
                "database": "connected",
                "vector_db": "connected", # Có thể thêm logic check qdrant_client.get_collections()
                "kafka": "running",
                "llm_provider": "active"
            },
            "stats": {
                "total_processed": total_articles,
                "last_run": time.strftime("%H:%M:%S")
            },
            "components": [
                {"name": "Crawler", "status": "idle", "processed": 120},
                {"name": "Kafka Producer", "status": "active", "processed": 120},
                {"name": "Spark/ETL", "status": "active", "processed": 115},
                {"name": "Vector Ingestion", "status": "active", "processed": 115}
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()
        
@app.get("/articles/{article_id}/chunks")
async def get_article_chunks_from_db(article_id: int):
    """Lấy danh sách các chunks của một bài báo trực tiếp từ Postgres Data Warehouse"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Lấy dữ liệu từ bảng fact_chunks
        cur.execute("""
            SELECT chunk_index, content 
            FROM fact_chunks 
            WHERE article_id = %s 
            ORDER BY chunk_index ASC
        """, (article_id,))
        
        records = cur.fetchall()
        
        # Format lại dữ liệu cho khớp với giao diện React
        formatted_chunks = []
        for row in records:
            formatted_chunks.append({
                "chunk_id": f"idx_{row['chunk_index']}",
                "text": row['content']
            })
            
        return {"status": "success", "total_chunks": len(formatted_chunks), "chunks": formatted_chunks}
    except Exception as e:
        logger.error(f"Lỗi khi lấy chunks cho article {article_id}: {e}")
        return {"status": "error", "message": str(e), "chunks": []}
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)