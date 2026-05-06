import psycopg2
from psycopg2 import pool

PG_CONFIG = {
    "dbname": "postgres",
    "user": "tuantran",
    "password": "tuantran",
    "host": "news-rag-cloud.cl2emq8kis9l.ap-southeast-2.rds.amazonaws.com",
    "port": "5432",
    "sslmode": "require"
}

def get_connection():
    """Hàm này trả về kết nối tới AWS RDS"""
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        return conn
    except Exception as e:
        print(f"Không thể kết nối AWS: {e}")
        return None
def check_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT version();")
    cur.execute("SELECT * FROM article_metadata LIMIT 5;")
    cur.execute(
    # Query thử bảng Fact sau khi đã chạy Crawler
    """
    SELECT a.title, s.domain, t.date 
    FROM fact_articles a
    JOIN dim_source s ON a.source_id = s.source_id
    JOIN dim_time t ON a.time_id = t.time_id
    LIMIT 5;
    """)
    print(cur.fetchall())
    cur.close()
    conn.close()    
if __name__ == "__main__":
    check_db()