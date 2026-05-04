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
async def list_articles(limit: int = 10, offset: int = 0):
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, title, url, source_id, published_date 
            FROM article_metadata 
            ORDER BY published_date DESC 
            LIMIT %s OFFSET %s
        """, (limit, offset))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

@app.get("/stats")
async def get_stats():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sources")
        s_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM article_metadata")
        a_count = cur.fetchone()[0]
        return {"total_sources": s_count, "total_articles": a_count}
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)