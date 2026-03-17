import multiprocessing
import consumer  # Import file vừa viết
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from crawler.spider import NewsRAGSpider

def run_spider():
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    process.crawl(NewsRAGSpider)
    process.start()

def run_consumer():
    consumer.start_processing()

if __name__ == "__main__":
    p1 = multiprocessing.Process(target=run_spider)
    p2 = multiprocessing.Process(target=run_consumer)

    p2.start() # Chạy Consumer trước để đợi sẵn
    p1.start() # Chạy Spider để bắt đầu crawl

    p1.join()
    p2.join()