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
                soup.select_one(".author-name")
            )
            if author_elem:
                article_data["author"] = author_elem.get_text().strip()
            
            # Extract content
            content_elem = (
                soup.select_one("div.post-content") or
                soup.select_one("div.article-content") or
                soup.select_one("div.content")
            )
            
            if content_elem:
                # Clean up content
                for elem in content_elem.select(".social-share, .tags, .related-posts, script, style"):
                    elem.decompose()
                
                article_data["content"] = str(content_elem)
                article_data["markdown"] = self.clean_markdown(h2t.handle(str(content_elem)))
                article_data["success"] = True
            
            return article_data
            
        except Exception as e:
            print(f"Error extracting data from {url}: {e}")
            return article_data
    
    def clean_markdown(self, markdown_text):
        """
        Clean up markdown text by removing extra whitespace and formatting issues.
        
        Args:
            markdown_text: Raw markdown text
            
        Returns:
            Cleaned markdown text
        """
        # Remove multiple consecutive blank lines
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
        
        # Fix image links
        markdown_text = re.sub(r'!\[\]\((.*?)\)', r'![](\1)', markdown_text)
        
        return markdown_text.strip()
    
    def create_safe_filename(self, title, max_length=50):
        """
        Create a safe filename from the article title.
        
        Args:
            title: Article title
            max_length: Maximum length of the filename
            
        Returns:
            Safe filename string
        """
        # Replace non-alphanumeric characters with underscores
        safe_title = re.sub(r'[^a-zA-Z0-9]+', '_', title.lower())
        
        # Trim to max_length
        if len(safe_title) > max_length:
            safe_title = safe_title[:max_length]
        
        # Remove trailing underscores
        safe_title = safe_title.rstrip('_')
        
        return safe_title
    
    def save_article(self, article_data):
        """
        Save article data as markdown and JSON.
        
        Args:
            article_data: Dictionary with article data
            
        Returns:
            Path to the saved markdown file
        """
        if not article_data["success"]:
            return None
            
        try:
            # Create safe filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = self.create_safe_filename(article_data["title"])
            filename_base = f"{timestamp}_{safe_title}"
            
            # Save as markdown
            md_path = self.output_path / f"{filename_base}.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# {article_data['title']}\n\n")
                if article_data["date"]:
                    f.write(f"**Date:** {article_data['date']}\n\n")
                if article_data["author"]:
                    f.write(f"**Author:** {article_data['author']}\n\n")
                f.write(f"**Source:** [{article_data['url']}]({article_data['url']})\n\n")
                f.write(article_data["markdown"])
            
            # Save as JSON
            json_path = self.output_path / f"{filename_base}.json"
            json_data = {
                "title": article_data["title"],
                "date": article_data["date"],
                "author": article_data["author"],
                "url": article_data["url"],
                "markdown": article_data["markdown"]
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            print(f"Article saved: {md_path}")
            return md_path
            
        except Exception as e:
            print(f"Error saving article {article_data['title']}: {e}")
            return None
    
    def process_articles(self):
        """
        Process articles from all categories.
        
        Returns:
            Dictionary with crawling statistics
        """
        all_links = set()
        
        # Fetch article links from all categories
        for category in CATEGORIES:
            links = self.fetch_article_links(category)
            print(f"Found {len(links)} links in category: {category or 'homepage'}")
            # Add new links to our set
            all_links.update(links)
            
            # Wait to avoid overloading the server
            time.sleep(random.uniform(1, 3))
        
        print(f"Total unique links found: {len(all_links)}")
        
        # Process each article
        for url in list(all_links)[:self.max_articles]:
            # Skip if already visited
            if url in self.visited_urls:
                continue
                
            self.visited_urls.add(url)
            self.stats["articles_fetched"] += 1
            
            # Fetch and process article
            html_content = self.fetch_article_content(url)
            if not html_content:
                self.stats["failed_scrapes"] += 1
                continue
                
            # Extract article data
            article_data = self.extract_article_data(html_content, url)
            
            # Save article
            if article_data["success"]:
                self.save_article(article_data)
                self.stats["successful_scrapes"] += 1
                self.stats["articles"].append({
                    "url": article_data["url"],
                    "title": article_data["title"],
                    "date": article_data["date"],
                    "author": article_data["author"]
                })
            else:
                self.stats["failed_scrapes"] += 1
            
            # Wait to avoid overloading the server
            time.sleep(random.uniform(1, 3))
        
        # Save summary
        summary_path = self.output_path / "crawl_summary.json"
        self.stats["end_time"] = datetime.now().isoformat()
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        
        print(f"\nCrawling completed. Results saved to {self.output_path}")
        print(f"Articles fetched: {self.stats['articles_fetched']}")
        print(f"Successful: {self.stats['successful_scrapes']}")
        print(f"Failed: {self.stats['failed_scrapes']}")
        
        return self.stats

def main():
    """Parse arguments and run the crawler."""
    parser = argparse.ArgumentParser(description="U.Today Web Crawler")
    parser.add_argument("--output-dir", default="scraped_data", help="Directory to save scraped data")
    parser.add_argument("--max-articles", type=int, default=5, help="Maximum number of articles to fetch")
    
    args = parser.parse_args()
    
    crawler = UTodayWebCrawler(
        output_dir=args.output_dir,
        max_articles=args.max_articles
    )
    
    crawler.process_articles()

if __name__ == "__main__":
    main() 