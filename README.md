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

Dự án được thiết kế theo tiêu chuẩn module hóa Data Engineering:

```text
NEWS-RAG/
├── app/                    # Ứng dụng giao diện (Next.js / Dashboard)
│   └── src/                # Mã nguồn frontend và các components
├── config/                 # Cấu hình tập trung hệ thống
│   └── config_site.json    # Danh sách các trang báo cần thu thập
├── consumer/               # Pipeline xử lý dữ liệu từ Kafka sang Database thô
│   └── consumer.py
├── crawler/                # Lõi Scrapy (Spiders, Pipelines, Settings)
│   ├── spiders/
│   │   └── spider.py       # Lõi thu thập link và trích xuất nội dung
│   ├── pipelines.py        # Xử lý dữ liệu sau khi thu thập
│   └── settings.py         # Cấu hình Scrapy (User-Agent, Delay...)
├── database/               # Scripts khởi tạo cấu trúc dữ liệu
│   └── warehouse.sql       # Định nghĩa Star Schema cho Data Warehouse
├── etl/                    # Tiến trình Biến đổi và Nạp dữ liệu (Transform & Load)
│   └── etl_warehouse.py    # Script ETL chính
├── vectorize/              # Xử lý nhúng AI và Vector Database
│   ├── vectorize.py        # Chuyển đổi văn bản sang Vector và đẩy lên Qdrant
│   └── reset_qdrant.py     # Xóa và khởi tạo lại bộ nhớ Vector
├── search/                 # Hệ thống truy vấn RAG và tích hợp LLM
│   ├── engine.py           # Điều phối luồng (Retriever -> Generator)
│   ├── generator.py        # Quản lý các mô hình ngôn ngữ lớn (OpenAI, Gemini...)
│   ├── retriever.py        # Logic kết nối và tìm kiếm trên Qdrant
│   ├── prompts.py          # Quản lý các mẫu gợi ý cho AI
│   └── schemas.py          # Định nghĩa cấu trúc dữ liệu Pydantic
├── main.tf                 # Cấu hình hạ tầng Cloud (Terraform)
├── deploy.sh               # Script triển khai tự động lên AWS Sydney
├── Dockerfile              # Đóng gói mã nguồn hệ thống
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
