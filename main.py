import os
import json
import multiprocessing
import time
import datetime
import consumer.consumer as consumer_module
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from crawler.spiders.spider import NewsRAGSpider

# Import 2 hàm xử lý AI của bạn
from etl.etl_warehouse import run_etl_warehouse
from vectorize.vectorize import run_vectorization

# --- CẤU HÌNH CA LÀM VIỆC ---
CRAWL_DURATION = 1 * 60  # 10 phút (tính bằng giây)
SHIFT_DURATION = 1 * 3600 # 8 tiếng/ca (1 ngày 3 ca)

def run_spider(site_url):
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    process.crawl(NewsRAGSpider, start_urls=[site_url])
    process.start()

def run_consumer():
    print("[Consumer] Đang khởi tạo kết nối...")
    time.sleep(2) 
    consumer_module.start_processing()

def run_crawling_phase(urls):
    """Giai đoạn 1: Bật Crawl và Consumer trong đúng 10 phút rồi ép dừng"""
    print(f"\n{'='*50}")
    print(f"BẮT ĐẦU CA CRAWL DỮ LIỆU: {datetime.datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*50}")
    
    all_processes = []
    
    # 1. Bật Consumer
    p_cons = multiprocessing.Process(target=run_consumer, name="Consumer-Process")
    p_cons.start()
    all_processes.append(p_cons)
    time.sleep(5)
    
    # 2. Bật Spiders
    for url in urls:
        p_spider = multiprocessing.Process(target=run_spider, args=(url,), name=f"Spider-{url}")
        p_spider.start()
        all_processes.append(p_spider)
        
    # 3. Canh đúng 10 phút
    print(f"[*] Các máy cào đang chạy. Sẽ tự động ngắt sau {CRAWL_DURATION/60} phút...")
    time.sleep(CRAWL_DURATION)
    
    # 4. Tới giờ -> Ép dừng toàn bộ để chuyển phase
    print("[*] Đã hết 10 phút! Đang ngắt Crawler và Consumer để chuyển sang AI...")
    for p in all_processes:
        if p.is_alive():
            p.terminate()
            p.join()
            
    print("[OK] Đã dọn dẹp xong tiến trình cào dữ liệu.")

def run_processing_phase(end_time):
    """Giai đoạn 2: Vòng lặp Micro-batching ETL và Vectorize cho đến ca tiếp theo"""
    print(f"\n{'='*50}")
    print(f"BẮT ĐẦU CA XỬ LÝ AI (ETL & VECTORIZE)")
    print(f"{'='*50}")
    
    while time.time() < end_time:
        print("\n--- [Micro-Batch] Đang chạy lô mới ---")
        # ETL lấy 50 bài báo mới
        etl_count = run_etl_warehouse(limit=50) 
        
        # Vectorize lấy 256 chunks mới đẩy lên Qdrant
        vec_count = run_vectorization(limit=256)

        if etl_count == 0 and vec_count == 0:
            print("[Zzz] Dữ liệu đã Up-to-date. Nghỉ 2 phút chờ bài mới...")
            time.sleep(120) 
        else:
            print(f"[OK] Hoàn tất lô: {etl_count} bài báo, {vec_count} chunks vector. Tiếp tục ngay...")
            
    print("[!] Đã đến giờ ca mới. Tạm ngắt tiến trình xử lý...")


def main_pipeline():
    multiprocessing.set_start_method('spawn', force=True)
    
    config_path = 'config/config_site.json'
    if not os.path.exists(config_path):
        print(f" Không tìm thấy file config tại: {config_path}")
        return
        
    with open(config_path, 'r', encoding='utf-8') as f:
        sites = json.load(f)
    urls = [s['url'] if isinstance(s, dict) else s for s in sites]

    try:
        while True: 
            shift_start = time.time()
            shift_end = shift_start + SHIFT_DURATION
            
            # Phase 1: Cào 10 phút
            run_crawling_phase(urls)
            
            # Phase 2: Xử lý trong phần thời gian còn lại của ca 
            run_processing_phase(shift_end)
            
    except KeyboardInterrupt:
        print("\nNgười dùng yêu cầu dừng hệ thống toàn diện...")

if __name__ == "__main__":
    main_pipeline()