import json
from confluent_kafka import Producer

class KafkaPipeline:
    def __init__(self):
        # Thiết lập Producer kết nối tới Kafka local
        self.producer = Producer({
            'bootstrap.servers': 'localhost:9092',
            'client.id': 'scrapy-news-collector'
        })

    def process_item(self, item, spider):
        try:
            # Chuyển Item thành JSON string
            line = json.dumps(dict(item), ensure_ascii=False)
            # Gửi vào topic news_raw
            self.producer.produce('news_raw', value=line.encode('utf-8'))
            self.producer.flush() 
        except Exception as e:
            spider.logger.error(f"Lỗi gửi Kafka: {e}")
        return item