import os
import json
import re
import platform
import scrapy
from newspaper import Article
from datetime import datetime

class NewsRAGSpider(scrapy.Spider):
    name = 'news_rag_spider'
    
    is_windows = platform.system() == "Windows"
    
    custom_settings = {
        'CONCURRENT_REQUESTS': 16 if is_windows else 32,
        'DOWNLOAD_DELAY': 1.0 if is_windows else 0.5,
        'DEPTH_LIMIT': 5,
        'ROBOTSTXT_OBEY': False,
        'LOG_LEVEL': 'INFO',
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            if is_windows else
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        config_filename = 'config_site.json'
        config_path = os.path.abspath(os.path.join(curr_dir, config_filename))

        if not os.path.exists(config_path):
            self.logger.error(f"Không tìm thấy file: {config_path}")
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            sites = json.load(f)
        self.start_urls = [s['url'] if isinstance(s, dict) else s for s in sites]

    def parse(self, response):
        curr_domain = scrapy.utils.url.parse_url(response.url).netloc
        all_links = response.css('a::attr(href)').getall()
        
        for link in all_links:
            if any(link.startswith(x) for x in ['mailto:', 'tel:', 'javascript:', '#']):
                continue
                
            full_url = response.urljoin(link)
            
            if curr_domain in full_url:
                if any(ext in full_url for ext in ['.html', '.htm', '.amp']):
                    yield response.follow(full_url, callback=self.parse_article)
                elif len(full_url.replace('https://' + curr_domain, '').split('/')) <= 3:
                    yield response.follow(full_url, callback=self.parse)

    def parse_article(self, response):
        article = Article(response.url)
        article.set_html(response.text)
        try:
            article.parse()
        except:
            return

        if not article.text or len(article.text) < 100:
            return

        # ----- AUTHOR (Quét mẻ lưới lớn các định dạng lạ) -----
        author_list = article.authors
        author = ", ".join(author_list).strip() if author_list else ""

        if not author:
            author_selectors = [
                response.css('.article-detail-author__info .name a::text').get(), # Vietnamnet mobile
                response.css('.author-name a::text').get(), # Dân trí E-magazine
                response.css('.news-detail-project::text').get(), # Vietnamnet chuyên đề
                response.css('[rel="author"]::text').get(),
                response.css('p[style*="text-align:right"] strong::text').get(),
                response.css('p[style*="text-align: right"] strong::text').get(),
                response.css('p.author_mail strong::text').get(),
                response.css('.author::text').get()
            ]
            for a in author_selectors:
                if a and a.strip() and a.strip() != "Unknown":
                    author = a.strip()
                    break
        
        # Kế hoạch B: Bắt thẻ in đậm cuối cùng của bài viết
        if not author or author == "Unknown":
            possible_authors = response.css('p strong::text, p b::text').getall()
            if possible_authors:
                for possible_author in reversed(possible_authors):
                    clean_name = possible_author.strip()
                    if 2 <= len(clean_name) <= 30:
                        author = clean_name
                        break

        author = author if author else "Unknown"

        # ----- PUBLISH DATE (Chiến thuật Evaluate All - Duyệt đến khi thành công) -----
        p_date = None
        
        # Tập hợp tất cả các class giấu ngày tháng có thể có
        raw_dates = [
            response.css('meta[property="article:published_time"]::attr(content)').get(),
            response.css('time::attr(datetime)').get(),
            response.css('time::text').get(), # Dân trí E-magazine
            response.css('meta[name="pubdate"]::attr(content)').get(),
            response.css('.publish-date::text').get(), # Vietnamnet
            response.css('.bread-crumb-detail__time::text').get(), # Vietnamnet mobile
            response.css('.bread-crumb__detail-time p::text').get(), # Vietnamnet chuyên đề
            response.css('.bread-crumb__detail-time::text').get(),
            response.css('[data-role="publishdate"]::text').get(),
            response.css('.detail-time div::text').get(),
            response.css('.detail-time::text').get(),
            response.css('span.date::text').get(),
            response.css('.time-now::text').get()
        ]
        
        for raw_date in raw_dates:
            if not raw_date or not raw_date.strip():
                continue
                
            # Làm sạch chuỗi
            clean_date = re.sub(r'\s+', ' ', raw_date).replace('\xa0', ' ').strip()
            
            try:
                # 1. ISO (VD: 2026-04-06 19:33 hoặc 2026-04-06T19:33:00)
                match_iso = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})(?:T|\s+)(\d{1,2}):(\d{1,2})', clean_date)
                if match_iso:
                    y, m, d, h, minute = match_iso.groups()
                    p_date = datetime(int(y), int(m), int(d), int(h), int(minute))
                    break # THÀNH CÔNG -> Thoát vòng lặp ngay!
                
                # 2. Ngày trước Giờ sau (VD: 6/4/2026, 17:02)
                match_vn = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4}).*?(\d{1,2}):(\d{1,2})', clean_date)
                if match_vn:
                    d, m, y, h, minute = match_vn.groups()
                    p_date = datetime(int(y), int(m), int(d), int(h), int(minute))
                    break
                    
                # 3. Giờ trước Ngày sau (VD: 14:29 06/02/2024)
                match_vn_rev = re.search(r'(\d{1,2}):(\d{1,2}).*?(\d{1,2})[/-](\d{1,2})[/-](\d{4})', clean_date)
                if match_vn_rev:
                    h, minute, d, m, y = match_vn_rev.groups()
                    p_date = datetime(int(y), int(m), int(d), int(h), int(minute))
                    break
                    
                # 4. Chỉ có ngày
                match_date = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', clean_date)
                if match_date:
                    d, m, y = match_date.groups()
                    p_date = datetime(int(y), int(m), int(d))
                    break
                    
            except Exception:
                continue # Nếu lỗi ở chuỗi này, bỏ qua và lấy chuỗi tiếp theo
                
        if not p_date:
            p_date = article.publish_date

        publish_date = p_date.strftime("%Y-%m-%d %H:%M:%S") if p_date else "Unknown"

        yield {
            'title': article.title.strip(),
            'content': article.text.strip(),
            'url': response.url,
            'source': scrapy.utils.url.parse_url(response.url).netloc,
            'author': author,
            'publish_date': publish_date
        }