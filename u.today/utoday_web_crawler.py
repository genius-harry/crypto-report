#!/usr/bin/env python3
"""
U.Today Web Crawler

This script crawls U.Today to fetch cryptocurrency news articles.
It extracts content using direct web scraping and saves articles in markdown and JSON formats.
"""

import os
import sys
import json
import time
import random
import re
import argparse
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import html2text

# Configure HTML to Text converter
h2t = html2text.HTML2Text()
h2t.ignore_links = False
h2t.ignore_images = True
h2t.ignore_tables = True
h2t.ignore_emphasis = True
h2t.body_width = 0  # No wrapping

# Base URL
BASE_URL = "https://u.today"
CATEGORIES = ["", "bitcoin-news", "ethereum-news", "ripple-and-xrp-news", "cardano-news", "shiba-inu-news", "dogecoin-news"]

class UTodayWebCrawler:
    """Crawler for u.today that uses direct web scraping."""
    
    def __init__(self, output_dir: str = "scraped_data", max_articles: int = 5):
        """
        Initialize the crawler.
        
        Args:
            output_dir: Directory to save scraped data
            max_articles: Maximum number of articles to fetch
        """
        self.output_dir = output_dir
        self.max_articles = max_articles
        self.session = self._setup_session()
        self.visited_urls = set()
        
        # Create output directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_path = Path(output_dir) / timestamp
        os.makedirs(self.output_path, exist_ok=True)
        
        # Setup statistics tracking
        self.stats = {
            "start_time": datetime.now().isoformat(),
            "articles_fetched": 0,
            "successful_scrapes": 0,
            "failed_scrapes": 0,
            "articles": []
        }
    
    def _setup_session(self) -> requests.Session:
        """Set up and configure requests session with browser-like headers."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
            "Cache-Control": "max-age=0",
        })
        return session
    
    def fetch_article_links(self, category=""):
        """
        Fetch article links from the main page or category pages.
        
        Args:
            category: Category to fetch articles from (empty for homepage)
            
        Returns:
            List of article URLs
        """
        url = f"{BASE_URL}/{category}" if category else BASE_URL
        try:
            print(f"Fetching article links from: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            article_links = []
            
            # Find news__item divs
            news_items = soup.select("div.news__item")
            if news_items:
                print(f"Found {len(news_items)} news items")
                for item in news_items:
                    link_elem = item.select_one("a")
                    if link_elem and link_elem.has_attr("href"):
                        href = link_elem["href"]
                        if href.startswith("/"):
                            full_url = f"{BASE_URL}{href}"
                            article_links.append(full_url)
            
            # If no news items found, try header items
            if not article_links:
                header_items = soup.select("div.header-news__item")
                print(f"Found {len(header_items)} header news items")
                for item in header_items:
                    link_elem = item.select_one("a")
                    if link_elem and link_elem.has_attr("href"):
                        href = link_elem["href"]
                        if href.startswith("/"):
                            full_url = f"{BASE_URL}{href}"
                            article_links.append(full_url)
            
            # Limit to max_articles
            return article_links[:self.max_articles]
            
        except Exception as e:
            print(f"Error fetching article links from {url}: {e}")
            return []
    
    def fetch_article_content(self, url):
        """
        Fetch article content from the given URL.
        
        Args:
            url: URL of the article
            
        Returns:
            HTML content of the article or None if failed
        """
        try:
            print(f"Fetching article: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
            
        except Exception as e:
            print(f"Error fetching article {url}: {e}")
            return None
    
    def extract_article_data(self, html_content, url):
        """
        Extract article data from HTML content.
        
        Args:
            html_content: HTML content of the article
            url: URL of the article
            
        Returns:
            Dictionary with extracted article data
        """
        article_data = {
            "url": url,
            "title": "",
            "date": "",
            "author": "",
            "content": "",
            "markdown": "",
            "success": False
        }
        
        if not html_content:
            return article_data
            
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Extract title
            title_elem = (
                soup.select_one("h1.article-title") or 
                soup.select_one("h1.post-title") or
                soup.select_one("h1")
            )
            if title_elem:
                article_data["title"] = title_elem.get_text().strip()
            
            # Extract date
            date_elem = (
                soup.select_one(".article-date") or
                soup.select_one(".post-date") or
                soup.select_one("time")
            )
            if date_elem:
                article_data["date"] = date_elem.get_text().strip()
            
            # Extract author
            author_elem = (
                soup.select_one(".article-author") or
                soup.select_one(".post-author") or
                soup.select_one(".author")
            )
            if author_elem:
                article_data["author"] = author_elem.get_text().strip()
            
            # Extract content
            content_elem = (
                soup.select_one(".article-content") or
                soup.select_one(".post-content") or
                soup.select_one(".entry-content") or
                soup.select_one("article .content")
            )
            
            if content_elem:
                # Clean up content - remove unwanted elements
                for unwanted in content_elem.select(".social-share, .ad-container, .newsletter-container, .related-posts"):
                    unwanted.decompose()
                
                article_data["content"] = str(content_elem)
                article_data["markdown"] = self.clean_markdown(h2t.handle(str(content_elem)))
                article_data["success"] = True
            
            return article_data
            
        except Exception as e:
            print(f"Error extracting article data: {e}")
            return article_data
    
    def clean_markdown(self, markdown_text):
        """
        Clean up markdown text by removing extra spaces, fixing linebreaks, etc.
        
        Args:
            markdown_text: Original markdown text
            
        Returns:
            str: Cleaned markdown text
        """
        if not markdown_text:
            return ""
        
        # Remove consecutive blank lines
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
        
        # Remove extra spaces at the beginning of lines
        markdown_text = re.sub(r'^\s+', '', markdown_text, flags=re.MULTILINE)
        
        return markdown_text.strip()
    
    def create_safe_filename(self, title, max_length=50):
        """
        Create a safe filename from article title.
        
        Args:
            title: Article title
            max_length: Maximum length of the filename
            
        Returns:
            str: Safe filename
        """
        # Replace special characters and spaces
        filename = re.sub(r'[^\w\s-]', '', title.lower())
        filename = re.sub(r'[\s]+', '_', filename)
        
        # Truncate to max_length
        if len(filename) > max_length:
            filename = filename[:max_length]
        
        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"{timestamp}_{filename}"
    
    def save_article(self, article_data):
        """
        Save article data to markdown and JSON files.
        
        Args:
            article_data: Article data dictionary
            
        Returns:
            tuple: (markdown_path, json_path) or (None, None) if failed
        """
        if not article_data["success"]:
            return None, None
        
        try:
            # Create directories
            markdown_dir = self.output_path / "markdown"
            json_dir = self.output_path / "json"
            os.makedirs(markdown_dir, exist_ok=True)
            os.makedirs(json_dir, exist_ok=True)
            
            # Create safe filename
            filename = self.create_safe_filename(article_data["title"])
            
            # Save markdown
            markdown_content = f"# {article_data['title']}\n\n"
            
            if article_data["date"]:
                markdown_content += f"Date: {article_data['date']}\n\n"
                
            if article_data["author"]:
                markdown_content += f"Author: {article_data['author']}\n\n"
                
            markdown_content += f"Source: [U.Today]({article_data['url']})\n\n"
            markdown_content += "---\n\n"
            markdown_content += article_data["markdown"]
            
            markdown_path = markdown_dir / f"{filename}.md"
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
                
            # Save JSON (excluding HTML content to save space)
            json_data = {k: v for k, v in article_data.items() if k != "content"}
            json_path = json_dir / f"{filename}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
                
            print(f"Article saved: {markdown_path}")
            return markdown_path, json_path
            
        except Exception as e:
            print(f"Error saving article: {e}")
            return None, None
    
    def process_articles(self):
        """
        Process articles from categories.
        
        Returns:
            list: List of successfully processed articles
        """
        all_processed_articles = []
        
        for category in CATEGORIES:
            if len(all_processed_articles) >= self.max_articles:
                break
                
            remaining = self.max_articles - len(all_processed_articles)
            print(f"\nProcessing category: {category or 'home'} (remaining: {remaining})")
            
            article_links = self.fetch_article_links(category)
            if not article_links:
                print(f"No article links found for category: {category or 'home'}")
                continue
            
            # Process each article
            for link in article_links:
                if len(all_processed_articles) >= self.max_articles:
                    break
                    
                # Skip if already processed
                if link in self.visited_urls:
                    continue
                    
                self.visited_urls.add(link)
                self.stats["articles_fetched"] += 1
                
                # Fetch and process article
                html_content = self.fetch_article_content(link)
                if not html_content:
                    self.stats["failed_scrapes"] += 1
                    continue
                    
                article_data = self.extract_article_data(html_content, link)
                
                # Save article
                markdown_path, json_path = self.save_article(article_data)
                if markdown_path and json_path:
                    self.stats["successful_scrapes"] += 1
                    all_processed_articles.append(article_data)
                    
                    # Add to stats
                    self.stats["articles"].append({
                        "title": article_data["title"],
                        "url": article_data["url"],
                        "date": article_data["date"],
                        "saved_to": str(markdown_path)
                    })
                else:
                    self.stats["failed_scrapes"] += 1
                
                # Wait between requests
                time.sleep(random.uniform(1, 3))
        
        return all_processed_articles


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='U.Today Web Crawler')
    parser.add_argument('-a', '--articles', type=int, default=5, help='Maximum number of articles to fetch')
    parser.add_argument('-o', '--output', type=str, default='scraped_data', help='Output directory')
    
    args = parser.parse_args()
    
    crawler = UTodayWebCrawler(
        output_dir=args.output,
        max_articles=args.articles
    )
    
    # Process articles
    articles = crawler.process_articles()
    
    # Save summary
    crawler.stats["end_time"] = datetime.now().isoformat()
    summary_path = crawler.output_path / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(crawler.stats, f, ensure_ascii=False, indent=2)
        
    print(f"\nCrawling completed!")
    print(f"Articles fetched: {crawler.stats['articles_fetched']}")
    print(f"Successfully scraped: {crawler.stats['successful_scrapes']}")
    print(f"Failed scrapes: {crawler.stats['failed_scrapes']}")
    print(f"Summary saved to: {summary_path}")
    
    return crawler.stats["successful_scrapes"]


if __name__ == "__main__":
    main() 