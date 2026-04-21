import os
import psycopg2
import uuid
import time
from datetime import datetime
from dotenv import load_dotenv
from FlagEmbedding import BGEM3FlagModel 
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, SparseVectorParams, SparseVector

# --- ĐỊNH VỊ CHÍNH XÁC FILE .ENV ---
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(base_dir, '.env')
load_dotenv(dotenv_path)

# --- 1. CẤU HÌNH KẾT NỐI POSTGRESQL (Lấy từ .env) ---
PG_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)) # Ép kiểu số nguyên cho chắc chắn
}

# --- 2. CẤU HÌNH QDRANT CLOUD (Lấy từ .env) ---
QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME")

def generate_uuid(article_id, chunk_index):
    """Tạo một UUID cố định vĩnh viễn dựa trên article_id và chunk_index"""
    unique_string = f"article_{article_id}_chunk_{chunk_index}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))

def run_vectorization():
    print("[*] Đang tải mô hình BAAI/bge-m3 (Phiên bản Hybrid)...")
    model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True) 
    
    # Kết nối lên Qdrant Cloud
    qdrant = QdrantClient(
        url=f"https://{QDRANT_HOST}", 
        api_key=QDRANT_API_KEY
    )
    
    # Cấu hình Qdrant nhận 2 Vector cùng lúc (Dense & Sparse)
    if not qdrant.collection_exists(COLLECTION_NAME):
        print(f"[*] Đang tạo collection Hybrid '{COLLECTION_NAME}' trong Qdrant...")
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "dense": VectorParams(size=1024, distance=Distance.COSINE)
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams()
            }
        )
    else:
        print(f"[*] Collection '{COLLECTION_NAME}' đã tồn tại.")

    # Khởi tạo biến rỗng để tránh lỗi UnboundLocalError
    conn = None
    cur = None

    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cur = conn.cursor()

        print("[*] Đang truy xuất toàn bộ chunks từ PostgreSQL (Kèm Metadata)...")
        # [CẬP NHẬT] JOIN thêm thời gian và tác giả
        query = """
            SELECT 
                c.article_id, c.chunk_index, c.content, a.title, m.url,
                COALESCE(t.date::text, 'Unknown') as publish_date,
                COALESCE(string_agg(DISTINCT au.author_name, ', '), 'Unknown') as authors
            FROM fact_chunks c 
            JOIN fact_articles a ON c.article_id = a.article_id
            JOIN article_metadata m ON a.url_hash = m.url_hash
            LEFT JOIN dim_time t ON a.time_id = t.time_id
            LEFT JOIN fact_article_authors faa ON a.article_id = faa.article_id
            LEFT JOIN dim_author au ON faa.author_id = au.author_id
            GROUP BY c.article_id, c.chunk_index, c.content, a.title, m.url, t.date
        """
        cur.execute(query)
        all_chunks = cur.fetchall()

        if not all_chunks:
            print("[!] Không có chunk nào trong Warehouse.")
            return

        print("[*] Đang đối chiếu với Qdrant để tìm các chunks mới...")
        chunks_to_process = []
        
        # Lọc Incremental Load
        for row in all_chunks:
            article_id, chunk_index, content, title, url, publish_date, authors = row
            point_id = generate_uuid(article_id, chunk_index)
            
            try:
                result = qdrant.retrieve(collection_name=COLLECTION_NAME, ids=[point_id])
                if not result:
                    chunks_to_process.append(row) # Đưa toàn bộ row vào danh sách
            except Exception:
                chunks_to_process.append(row)

        total_new_chunks = len(chunks_to_process)
        if total_new_chunks == 0:
            print("[SUCCESS] Dữ liệu Hybrid trên Qdrant đã Up-to-date!")
            return

        print(f"[*] Bắt đầu Vector hóa và đẩy {total_new_chunks} chunks MỚI lên Qdrant...")

        points = []
        for idx, row in enumerate(chunks_to_process):
            article_id, chunk_index, content, title, url, publish_date, authors = row
            point_id = generate_uuid(article_id, chunk_index)
            
            # --- 1. BIẾN ĐỔI THỜI GIAN THÀNH TIMESTAMP ---
            timestamp = 0
            if publish_date and publish_date != 'Unknown':
                try:
                    date_str = str(publish_date)[:10] 
                    dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    timestamp = int(time.mktime(dt_obj.timetuple()))
                except Exception:
                    timestamp = 0

            # --- 2. VECTOR HÓA BẰNG MÔ HÌNH ---
            output = model.encode([content], return_dense=True, return_sparse=True)
            
            # Bóc tách Dense Vector
            dense_vec = output['dense_vecs'][0].tolist()
            
            # Bóc tách và Lọc Sparse Vector (Max Pooling)
            lexical_dict = output['lexical_weights'][0]
            sparse_dict = {}
            for token_str, weight in lexical_dict.items():
                token_id = model.tokenizer.convert_tokens_to_ids(token_str)
                if isinstance(token_id, list):
                    if not token_id: continue
                    token_id = token_id[0]
                
                token_id = int(token_id)
                weight = float(weight)
                
                if token_id in sparse_dict:
                    sparse_dict[token_id] = max(sparse_dict[token_id], weight)
                else:
                    sparse_dict[token_id] = weight
            
            token_ids = list(sparse_dict.keys())
            weights = list(sparse_dict.values())
            
            # --- 3. ĐÓNG GÓI POINT LÊN QDRANT ---
            point = PointStruct(
                id=point_id, 
                vector={
                    "dense": dense_vec,
                    "sparse": SparseVector(indices=token_ids, values=weights)
                },
                payload={
                    "article_id": article_id,
                    "chunk_index": chunk_index,
                    "title": title,
                    "url": url,
                    "content": content,
                    "authors": authors,
                    "publish_timestamp": timestamp # Dùng Timestamp để AI nhạy cảm với thời gian
                }
            )
            points.append(point)
            
            if len(points) >= 100:
                qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
                points = []
                print(f"  [+] Đã đẩy {idx + 1}/{total_new_chunks} chunks mới lên Qdrant...")

        if points:
            qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
            print(f"  [+] Đã đẩy {total_new_chunks}/{total_new_chunks} chunks mới lên Qdrant...")

        print("\n[SUCCESS] Đã nạp thành công dữ liệu HYBRID vào Qdrant Vector DB!")

    except Exception as e:
        print(f"[ERROR] Quá trình thất bại: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()

if __name__ == "__main__":
    run_vectorization()