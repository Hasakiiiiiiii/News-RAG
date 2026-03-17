import json
import hashlib
import oracledb
from confluent_kafka import Consumer
from pymongo import MongoClient

# --- CẤU HÌNH KẾT NỐI ---
MONGO_URI = "mongodb://tuan:tuan@localhost:27017/"
ORACLE_CONFIG = {
    "user": "system",
    "password": "tuan_password",
    "dsn": "localhost:1521/FREEPDB1"
}

# Kết nối MongoDB
client = MongoClient(MONGO_URI)
db = client["news_rag"]
collection = db["articles"]

# Kết nối Oracle (Chế độ Thin - cực hợp với Arch Linux)
def get_oracle_conn():
    return oracledb.connect(
        user=ORACLE_CONFIG["user"],
        password=ORACLE_CONFIG["password"],
        dsn=ORACLE_CONFIG["dsn"]
    )

# Cấu hình Kafka
conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'news_rag_group',
    'auto.offset.reset': 'earliest'
}
consumer = Consumer(conf)
consumer.subscribe(['news_raw'])

def start_processing():
    print(" [Consumer] Đang chạy Hybrid Pipeline (Oracle + MongoDB)...")
    
    # Mở kết nối Oracle một lần để dùng lại
    orcl_conn = get_oracle_conn()
    
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None: continue
            if msg.error():
                print(f"[ERROR] Kafka: {msg.error()}")
                continue

            # 1. Parse dữ liệu từ Kafka
            data = json.loads(msg.value().decode('utf-8'))
            url = data.get('url', '')
            title = data.get('title', 'No Title')
            
            if not url: continue

            # 2. Tạo URL Hash để chống trùng (Deduplication)
            url_hash = hashlib.sha256(url.encode()).hexdigest()

            # 3. Check Oracle trước (Oracle gác cổng)
            with orcl_conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM ARTICLE_METADATA WHERE url_hash = :1", [url_hash])
                if cursor.fetchone():
                    print(f"[INFO] Skip aready exist: {title[:50]}...")
                    continue

                # 4. Nếu chưa có, lưu nội dung thô vào MongoDB
                # Dùng update_one với upsert để chắc chắn 100% không trùng trong Mongo
                mongo_result = collection.update_one(
                    {"url": url},
                    {"$set": data},
                    upsert=True
                )
                
                # Lấy ObjectID từ Mongo để liên kết sang Oracle
                # Nếu là insert mới, lấy upserted_id, nếu update thì tìm lại id
                if mongo_result.upserted_id:
                    mongo_id = str(mongo_result.upserted_id)
                else:
                    existing_doc = collection.find_one({"url": url}, {"_id": 1})
                    mongo_id = str(existing_doc["_id"])

                # 5. Lưu Metadata vào Oracle để quản lý
                try:
                    cursor.execute("""
                        INSERT INTO ARTICLE_METADATA (url_hash, title, url, mongo_id) 
                        VALUES (:1, :2, :3, :4)
                    """, [url_hash, title, url, mongo_id])
                    orcl_conn.commit()
                    print(f" [Hybrid Success] Đã lưu mới: {title[:50]}...")
                except oracledb.Error as e:
                    print(f" [ERROR] Lỗi Oracle Insert: {e}")

    except KeyboardInterrupt:
        print("\n [Consumer]   Đang dừng Consumer...")
    finally:
        consumer.close()
        orcl_conn.close()

if __name__ == "__main__":
    start_processing()