# News RAG: Nền tảng Tổng hợp Dữ liệu và Phân tích AI

> Hệ thống Data Pipeline end-to-end: Tự động thu thập tin tức, xử lý luồng dữ liệu thời gian thực, chuẩn hóa kho dữ liệu và truy vấn thông minh với kiến trúc RAG.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Scrapy](https://img.shields.io/badge/Scrapy-Crawler-green.svg)
![Next.js](https://img.shields.io/badge/Next.js-Frontend-black.svg)
![AWS](https://img.shields.io/badge/AWS-Fargate%20%26%20ECS-orange.svg)
![Database](https://img.shields.io/badge/Database-PostgreSQL%20%26%20Qdrant-336791.svg)

---

## Tổng quan dự án

News RAG là một hệ thống phân tích dữ liệu toàn diện được thiết kế để giải quyết bài toán thu thập và xử lý tin tức từ các nguồn báo chí điện tử lớn (VnExpress, Dân Trí, VietnamNet). Dự án cung cấp nền tảng backend vững chắc để xây dựng các ứng dụng Chatbot AI có khả năng trả lời câu hỏi dựa trên ngữ cảnh thực tế, đảm bảo tính chính xác và cập nhật của thông tin.

### Các thành tựu thực tế đạt được

- **Triển khai Cloud thành công**: Toàn bộ hệ thống đã được vận hành trên AWS Sydney sử dụng kiến trúc Serverless (Fargate).
- **Hệ thống Web trực tuyến**: Giao diện người dùng hiện đại đã khả dụng tại địa chỉ: [http://bigdata-alb-611625925.ap-southeast-2.elb.amazonaws.com](http://bigdata-alb-611625925.ap-southeast-2.elb.amazonaws.com)
- **Tự động hóa hoàn toàn**: Pipeline dữ liệu được kích hoạt tự động hàng ngày thông qua AWS EventBridge.
- **Tối ưu hóa tài nguyên**: Xây dựng quy trình CI/CD rút gọn với Docker và Terraform, giúp triển khai nhanh chóng và tiết kiệm chi phí.

---

## Các tính năng nổi bật

### Hệ thống Pipeline dữ liệu
- Tự động hóa hoàn toàn: Quy trình từ thu thập đến lưu trữ được điều phối tự động.
- Xử lý ETL chuyên sâu: Làm sạch HTML, loại bỏ trùng lặp bằng URL Hash và chia nhỏ nội dung (Chunking).
- Lưu trữ đa tầng: Quản lý dữ liệu từ giai đoạn thô (Landing) đến giai đoạn tinh lọc (Warehouse).

### Hệ thống truy vấn AI (RAG)
- Hỗ trợ đa mô hình: Tích hợp linh hoạt Groq (Qwen, Llama), Google Gemini, OpenAI và Ollama.
- Cơ chế Scaling LLM: Cho phép thay đổi số lượng và loại mô hình chỉ thông qua file cấu hình .env.
- Generator Registry: Quản lý tập trung các thực thể mô hình thông qua Pattern Singleton và Registry.
- Tìm kiếm lai (Hybrid Search): Kết hợp tìm kiếm vector và tìm kiếm truyền thống để tối ưu kết quả.

### Giao diện và Giám sát
- Dashboard tương tác: Hiển thị thống kê dữ liệu và trạng thái vận hành của hệ thống.
- Pipeline Monitor: Giám sát thời gian thực các luồng dữ liệu đang chạy trên Cloud.
- AI Chat Interface: Giao diện trò chuyện thông minh với khả năng trích dẫn nguồn tin tức.

---

## Kiến trúc hệ thống

```text
┌────────────────┐      ┌────────────────┐      ┌────────────────┐
│ Nguồn dữ liệu  │─────▶│ Lớp Thu thập   │─────▶│ Lớp Xử lý      │
│ (Báo điện tử)  │      │ (Scrapy/Kafka) │      │ (ETL/Warehouse)│
└────────────────┘      └────────────────┘      └──────┬─────────┘
                                                       │
                                                       ▼
┌────────────────┐      ┌────────────────┐      ┌────────────────┐
│ Giao diện      │      │ Hệ thống RAG   │      │ Lưu trữ Vector │
│ (Next.js App)  │◀─────│ (AI Engine)    │◀─────│ (Qdrant DB)    │
└──────┬─────────┘      └────────────────┘      └────────────────┘
       │
       ▼
┌────────────────┐
│ Người dùng     │
│ (Hỏi đáp AI)   │
└────────────────┘
```

---

## Cấu trúc thư mục chi tiết

```text
.
├── app/                    # Ứng dụng Web & API Dashboard
│   ├── frontend/           # Giao diện Next.js (Dashboard, Chat, Monitor)
│   ├── api.py              # FastAPI backend cho ứng dụng
│   └── main.py             # Entry point khởi chạy ứng dụng
├── crawler/                # Lõi thu thập dữ liệu (Scrapy)
│   ├── spiders/spider.py   # Logic trích xuất nội dung tin tức
│   ├── pipelines.py        # Đẩy dữ liệu vào Kafka
│   └── settings.py         # Cấu hình hiệu năng và User-Agent
├── consumer/               # Pipeline xử lý dữ liệu
│   └── consumer.py         # Đọc từ Kafka và lưu vào Postgres (Metadata)
├── etl/                    # Transform & Load
│   └── etl_warehouse.py    # Làm sạch dữ liệu và nạp vào Warehouse
├── search/                 # Hệ thống RAG Engine
│   ├── engine.py           # Điều phối luồng Retriever -> Generator
│   ├── retriever.py        # Tìm kiếm ngữ nghĩa trên Qdrant
│   ├── generator.py        # Tích hợp các LLM (Groq, Gemini, OpenAI)
│   └── prompts.py          # Quản lý các Template cho AI
├── vectorize/              # Embedding & Vector DB
│   ├── vectorize.py        # Chuyển đổi văn bản sang Vector (BGE-M3)
│   └── reset_qdrant.py     # Khởi tạo lại bộ nhớ Vector
├── evaluation/             # Đánh giá chất lượng
│   └── ragas_evaluation.py # Chạy đánh giá bằng framework Ragas
├── database/               # SQL Scripts
│   └── warehouse.sql       # Định nghĩa Schema Star cho Warehouse
├── init_db/                # Khởi tạo hệ thống
│   └── init_postgre.py     # Script khởi tạo Database ban đầu
├── main.py                 # File thực thi chính của hệ thống
├── Dockerfile              # Cấu hình Docker image cho toàn bộ pipeline
├── docker-compose.yml      # Điều phối các dịch vụ (DB, Kafka, Qdrant)
└── requirements.txt        # Danh sách thư viện Python cần thiết
```

---

## Chi tiết luồng dữ liệu

1. Thu thập dữ liệu: Spider bắt đầu quét các trang báo từ danh sách trong config_site.json.
2. Xử lý bài viết: Nếu phát hiện đường dẫn là bài viết mới, hệ thống sử dụng thư viện newspaper để trích xuất nội dung.
3. Luồng Streaming: Dữ liệu được KafkaPipeline gửi vào topic news_raw để đảm bảo không bị thất thoát.
4. Nạp dữ liệu thô: Consumer đọc từ Kafka, hash URL để tránh trùng lặp và lưu vào bảng article_metadata.
5. Kho dữ liệu: Tiến trình ETL làm sạch dữ liệu, cắt nhỏ nội dung thành các chunks và nạp vào Warehouse.
6. Vector hóa: Các chunks được nhúng bằng mô hình BAAI/bge-m3 thành vector 1024 chiều và đẩy lên Qdrant.
7. Truy vấn AI: Hệ thống nhận câu hỏi, tìm kiếm ngữ nghĩa trên Qdrant và sử dụng LLM để tổng hợp câu trả lời.

---

## Lịch trình tự động (Automation Schedule)

Hệ thống được thiết lập để vận hành tự động toàn phần thông qua **AWS EventBridge (CloudWatch Events)**:
- **Crawler Schedule**: Tự động kích hoạt lúc `01:00 AM UTC` (tương đương **08:00 AM giờ Việt Nam**) mỗi ngày.
- **Pipeline Workflow**: 
    1. **Thu thập**: Crawler lấy tin tức mới từ các trang báo.
    2. **Xử lý ETL**: Chuyển đổi dữ liệu từ thô sang kho dữ liệu (Warehouse) ngay sau khi thu thập.
    3. **Vectorize**: Tự động nhúng (embedding) và cập nhật vào Qdrant để sẵn sàng cho truy vấn AI.
- **Cơ chế**: Sử dụng EventBridge điều phối các ECS Fargate Tasks chạy theo chu trình khép kín, đảm bảo dữ liệu luôn được cập nhật mỗi sáng.

---

## Hướng dẫn vận hành

### Triển khai trên AWS Cloud
```bash
# 1. Cấu hình quyền truy cập AWS
aws configure

# 2. Triển khai tự động (Terraform + Docker)
chmod +x deploy.sh
./deploy.sh
```

### Các lệnh kiểm tra hệ thống
- Chạy giao diện chat CLI: `make test-interactive`
- Kiểm tra phản hồi của AI: `make test-gen`
- Kiểm tra tích hợp toàn bộ luồng: `make test-pipeline`
- Dọn dẹp cache hệ thống: `make clean`

---

## Lưu ý quan trọng
- Kết nối: Nếu không kết nối được Database hoặc Kafka, hãy kiểm tra lại Security Group trên AWS (mở cổng 5432 và 9092).
- Cấu hình: File consumer.py cần được điều chỉnh thông tin host nếu chạy trong các môi trường mạng khác nhau.
- Tài nguyên AI: Trong lần chạy đầu tiên, hệ thống sẽ tải mô hình bge-m3 (vài GB), hãy đảm bảo dung lượng ổ đĩa trống tối thiểu 10GB.

---


**Dự án được thực hiện phục vụ mục đích học tập tại Trường Đại học Bách Khoa TP.HCM.**
**Giảng viên hướng dẫn: TS. Nguyễn Quang Hùng.**
