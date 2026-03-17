import scrapy
from newspaper import Article
import json

class NewsRAGSpider(scrapy.Spider):
    name = 'news_universal'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Đọc danh sách site từ file config
        with open('sites.json', 'r') as f:
            self.start_urls = json.load(f)

    def parse(self, response):
        # Tự động tìm tất cả các link bài viết (Newspaper3k làm rất tốt việc này)
        # Hoặc dùng LxmlLinkExtractor của Scrapy để lấy link
        all_links = response.css('a::attr(href)').getall()
        
        for link in all_links:
            yield response.follow(link, callback=self.parse_article)

    def parse_article(self, response):
        # Dùng Newspaper3k để bóc tách nội dung
        article = Article(response.url)
        article.set_html(response.text)
        article.parse()

        yield {
            'title': article.title,
            'author': article.authors,
            'publish_date': article.publish_date,
            'content': article.text, # Nội dung cực sạch để làm RAG
            'top_image': article.top_image,
            'url': response.url,
            'source': response.url.split('/')[2] # Lấy domain làm source
        }