# News RAG (Crawler + Kafka + MongoDB)

## 1. Mục đích
Dự án thu thập tin tức tự động, gửi Kafka và lưu MongoDB để dùng tiếp RAG.

## 2. Init
- File cấu hình URL: `crawler/config_site.json`
- Spider: `crawler/spider.py`
- Pipeline Kafka: `crawler/pipeline.py`
- Consumer lưu Mongo: `consumer.py`
- Startup: `main.py`
- Docker compose: `docker-compose.yml`

## 3. Makefile
- `make init` (Tạo venv và cài đặt requirement)
- `make up` (chạy Docker)
- `make run` (chạy main)
- `make stop` (dừng container)


## 5. Kiểm tra Mongo
`docker exec -it mongo_news_rag mongo -u tuan -p tuan --eval "db.getSiblingDB('news_rag').articles.find().limit(5).pretty()"`

## 6. Thay site
Sửa `crawler/config_site.json`.


