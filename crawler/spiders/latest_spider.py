import scrapy
from urllib.parse import urlparse
from newspaper import Article
from datetime import datetime
import json
import os
import re

class LatestNewsSpider(scrapy.Spider):
    name = 'latest_news_spider'

    custom_settings = {
        'CONCURRENT_REQUESTS': 32,
        'DOWNLOAD_DELAY': 0.5,
        'DEPTH_LIMIT': 2,
        'ROBOTSTXT_OBEY': False,
        'LOG_LEVEL': 'INFO',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [
            'https://vnexpress.net/tin-tuc-24h',
            'https://dantri.com.vn/tin-moi-nhat.htm',
            'https://vietnamnet.vn/tin-tuc-24h',
            'https://tuoitre.vn/tin-moi-nhat.htm',
            'https://thanhnien.vn/tin-moi-24h.htm'
        ]

    def parse(self, response):
        curr_domain = urlparse(response.url).netloc
        all_links = response.css('a::attr(href)').getall()

        for link in all_links:
            full_url = response.urljoin(link)
            if curr_domain in full_url:
                if any(ext in full_url for ext in ['.html', '.htm']):
                    yield response.follow(full_url, callback=self.parse_article)

    def parse_article(self, response):
        article = Article(response.url)
        article.set_html(response.text)
        try:
            article.parse()
        except:
            return

        if not article.text or len(article.text) < 100:
            return

        # --- REUSE LOGIC FROM TUAN'S SPIDER ---
        def is_valid_author(name):
            clean_name = name.strip()
            if re.match(r'^\d+[\.\-\)]', clean_name) or '?' in clean_name or '!' in clean_name:
                return False
            if not name or len(name) < 2 or len(name) > 100:
                return False
            if len(re.findall(r'\d', name)) >= 7:
                return False
            name_lower = name.lower()
            if re.search(r'\d{1,2}[/-]\d{1,2}|\d{1,2}:\d{1,2}', name):
                return False
            bad_words = ['thứ hai', 'thứ ba', 'thứ tư', 'thứ năm', 'thứ sáu', 'thứ bảy', 'chủ nhật', 'ngày', 'tháng', 'năm', 'phút trước', 'giờ trước']
            if any(word in name_lower for word in bad_words):
                return False
            return True

        author_list = article.authors
        author = ", ".join(author_list).strip() if author_list else ""

        # Simple extraction if newspaper3k fails or gives generic names
        if not author or "vietnamnet" in author.lower() or "dân trí" in author.lower():
            selectors = [
                response.css('a[href*="tac-gia"]::text').get(),
                response.css('.author-name::text').get(),
                response.css('.tacgia::text').get()
            ]
            for s in selectors:
                if s and is_valid_author(s):
                    author = s.strip()
                    break

        # Date extraction
        p_date = article.publish_date
        if not p_date:
            raw_date = response.css('meta[property="article:published_time"]::attr(content)').get() or response.css('time::attr(datetime)').get()
            if raw_date:
                match_iso = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', raw_date)
                if match_iso:
                    y, m, d = match_iso.groups()
                    p_date = datetime(int(y), int(m), int(d))

        yield {
            'title': article.title.strip(),
            'content': article.text.strip(),
            'url': response.url,
            'source': urlparse(response.url).netloc,
            'author': author if author else "Unknown",
            'publish_date': p_date.strftime("%Y-%m-%d %H:%M:%S") if p_date else "Unknown"
        }
