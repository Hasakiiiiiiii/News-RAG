# News RAG (Crawler + Kafka + PostgreSQL)

## Tổng quan dự án
News RAG là hệ thống thu thập tin tức tự động, đẩy dữ liệu thô vào Kafka và lưu metadata bài viết vào PostgreSQL.
Hệ thống gồm: Scrapy spider, pipeline Kafka, consumer PostgreSQL, Docker Compose.

##  Mục tiêu
- Cào tin tức từ các trang được cấu hình
- Gửi JSON bài viết vào topic Kafka `news_raw`
- Consumer đọc Kafka, dedup theo URL hash và insert vào bảng PostgreSQL `article_metadata`

##  Thành phần chính
- `main.py`: Chạy 2 process (spider + consumer) với `multiprocessing`
- `crawler/spiders/spider.py`: Spider cào link và trích nội dung bài với `newspaper`
- `crawler/pipelines.py`: pipeline gửi item đến Kafka
- `consumer/consumer.py`: consumer đọc Kafka và lưu vào PostgreSQL
- `crawler/settings.py`: cài đặt Scrapy (pipeline, user-agent...)
- `crawler/spiders/config_site.json`: danh sách start URLs
- `docker-compose.yml`: Kafka, MongoDB, PostgreSQL

##  Chuẩn bị & chạy
### 1) Cài dependencies Python
```bash
make setup
```

### 2) Khởi động Docker Compose
```bash
make up
make down #Nếu muốn tắt
make reset #Để reset docker
```

### 3) Tạo bảng PostgreSQL (chỉ lần đầu)
```bash
docker exec -it postgres_news_rag psql -U tuan -d news_rag -c "CREATE TABLE IF NOT EXISTS article_metadata (url_hash text PRIMARY KEY, url text, title text, content jsonb);"
```

### 4) Chạy pipeline
```bash
python main.py
```

### 5) Kiểm tra dữ liệu PostgreSQL
```bash
docker exec -it postgres_news_rag psql -U tuan -d news_rag -c "SELECT url, title FROM article_metadata LIMIT 5;"
```

##  Cấu hình trang cào
Mở `crawler/spiders/config_site.json` và sửa danh sách URL (JSON array):
```json
["https://vnexpress.net/", "https://dantri.com.vn/", "https://vietnamnet.vn/"]
```

##  Chi tiết luồng dữ liệu
1. Spider bắt đầu từ `config_site.json`.
2. Duyệt link: nếu link `.html` là bài viết thì gọi `parse_article`; nếu link chuyên mục thì tiếp tục parse.
3. `parse_article` dùng `newspaper.Article` parse nội dung, yield item gồm URL/tiêu đề nội dung.
4. `KafkaPipeline` gửi item JSON vào topic `news_raw`.
5. `consumer` đọc topic, hash URL và insert vào `article_metadata` với `ON CONFLICT DO NOTHING` để tránh trùng.

##  Lưu ý quan trọng
- Nếu Kafka hoặc PostgreSQL không kết nối được, kiểm tra trạng thái container và cổng.
- `consumer/consumer.py` đang kết nối Kafka `localhost:9092` và PostgreSQL host `localhost`; chạy trên host hoặc container khác cần chỉnh lại.
- Spiders hiện chỉ parse `vnexpress.net` trong parse_article, nếu muốn mở rộng cần điều chỉnh logic lọc url.

##  Mở rộng
- Thêm cấu hình cho site khác (chỉ parse theo định dạng domain)
- Lưu đầy đủ metadata vào MongoDB hoặc vector DB cho RAG
- Thêm dockerfile/entrypoint để deploy app trong container

---