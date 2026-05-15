import os
import json
import multiprocessing
import time
import argparse
import schedule

import consumer.consumer as consumer_module
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from crawler.spiders.spider import NewsRAGSpider

from etl.etl_warehouse import run_etl_warehouse
from vectorize.vectorize import run_vectorization

def run_spider(site_url):
    """Hàm này chạy trong một Process riêng cho mỗi trang báo"""
    settings = get_project_settings()
    
    # Ép Spider tự động ngắt sau 10 phút (600 giây) để đảm bảo đúng ca
    settings.set('CLOSESPIDER_TIMEOUT', 300)
    
    process = CrawlerProcess(settings)
    process.crawl(NewsRAGSpider, start_urls=[site_url])
    process.start()

def run_consumer():
    """Hàm này chạy trong một Process riêng để hốt dữ liệu từ Kafka"""
    print("[Consumer] Đang khởi tạo kết nối...")
    time.sleep(2) 
    consumer_module.start_processing()

def do_crawl_stage():
    """Hàm thực thi việc cào và lưu vào Kafka/Database thô"""
    config_path = 'config/config_site.json'
    if not os.path.exists(config_path):
        print(f" Không tìm thấy file config tại: {config_path}")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        sites = json.load(f)
    urls = [s['url'] if isinstance(s, dict) else s for s in sites]

    all_processes = []
    p_cons = None

    try:
        # 1. CHẠY CONSUMER TRƯỚC
        p_cons = multiprocessing.Process(target=run_consumer, name="Consumer-Process")
        p_cons.start()
        all_processes.append(p_cons)
        print("Consumer đã sẵn sàng.")
        
        time.sleep(5) 

        # 2. CHẠY SPIDERS SONG SONG
        print(f"Bắt đầu kích hoạt {len(urls)} Spiders (Thời lượng: 10 phút)...")
        spider_processes = []
        for url in urls:
            p_spider = multiprocessing.Process(target=run_spider, args=(url,), name=f"Spider-{url}")
            p_spider.start()
            spider_processes.append(p_spider)
            all_processes.append(p_spider)

        # 3. ĐỢI SPIDERS CHẠY XONG HOẶC HẾT TIMEOUT
        for p in spider_processes:
            p.join()
        
        print("Tất cả Spiders đã cào xong hoặc hết giờ. Đợi Consumer xử lý nốt bài cuối...")
        time.sleep(20) 

        # 4. DỪNG CONSUMER
        if p_cons and p_cons.is_alive():
            p_cons.terminate()
            p_cons.join()
        print("Hệ thống cào đã dừng sạch sẽ.")

    except KeyboardInterrupt:
        print("\nNgười dùng yêu cầu dừng hệ thống...")
        for p in all_processes:
            if p.is_alive():
                p.terminate()
                p.join()

def do_balance_etl_and_vectorize():
    """Chạy luân phiên cân đối ETL và Vectorize để làm nhẹ bộ nhớ và tối ưu số vector nhất"""
    print("\n" + "="*50)
    print(" BẮT ĐẦU CHẠY CÂN ĐỐI ETL & VECTORIZE ")
    print("="*50)
    
    while True:
        print("\n---> Chạy 1 vòng ETL (Giới hạn 50 bài)...")
        # Giới hạn xử lý 50 bài mỗi lượt để giải phóng RAM
        etl_count = run_etl_warehouse(limit=50) 
        
        print("\n---> Chạy 1 vòng Vectorize (Giới hạn 256 chunks)...")
        # Giới hạn đẩy 256 chunks mỗi lượt
        vec_count = run_vectorization(limit=256)
        
        # Nếu cả 2 đều trả về 0 tức là đã xử lý sạch sẽ dữ liệu cũ
        if etl_count == 0 and vec_count == 0:
            print("\n[V] ĐÃ CHẠY XONG TOÀN BỘ PIPELINE. KHÔNG CÒN DỮ LIỆU TỒN ĐỌNG.")
            break
        
        time.sleep(2) # Nghỉ chút để giảm tải DB

def run_full_pipeline():
    """Chạy từ A-Z một luồng khép kín"""
    do_crawl_stage()
    do_balance_etl_and_vectorize()

if __name__ == "__main__":
    multiprocessing.set_start_method('spawn', force=True)

    # Cấu hình Argument Parser
    parser = argparse.ArgumentParser(description="Quản lý Pipeline News RAG")
    parser.add_argument('--mode', type=str, choices=['crawl', 'etl', 'vectorize', 'full', 'auto'], default='full',
                        help='Chế độ chạy: crawl (chỉ cào), etl (chỉ etl), vectorize (chỉ vector), full (cào+etl+vec), auto (chạy tự động 3 ca)')
    args = parser.parse_args()

    if args.mode == 'crawl':
        do_crawl_stage()
    elif args.mode == 'etl':
        run_etl_warehouse(limit=None)
    elif args.mode == 'vectorize':
        run_vectorization(limit=None)
    elif args.mode == 'full':
        run_full_pipeline()
    elif args.mode == 'auto':
        print("[AUTO] Hệ thống đã vào chế độ tự động hóa.")
        print("[AUTO] Lịch trình: 3 ca/ngày (08:00, 14:00, 20:00).")
        
        # Đặt lịch hẹn 3 ca mỗi ngày
        schedule.every().day.at("08:00").do(run_full_pipeline)
        schedule.every().day.at("14:00").do(run_full_pipeline)
        schedule.every().day.at("20:00").do(run_full_pipeline)
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(30) 
        except KeyboardInterrupt:
            print("[AUTO] Đã dừng tự động hóa.")