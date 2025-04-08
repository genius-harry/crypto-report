#!/usr/bin/env python3
"""
Cointelegraph.com RSS Crawler

This script crawls Cointelegraph.com via RSS feeds to avoid Cloudflare protection.
It fetches articles from the RSS feed and extracts content using requests library.
"""

import os
import sys
import json
import time
import random
import re
import argparse
import feedparser
import requests
from datetime import datetime
from urllib.parse import urljoin
from pathlib import Path
import html2text
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

# Configure HTML to Text converter
h2t = html2text.HTML2Text()
h2t.ignore_links = False
h2t.ignore_images = True
h2t.ignore_tables = True
h2t.ignore_emphasis = True
h2t.body_width = 0  # No wrapping

# Base URL and RSS feeds
BASE_URL = "https://cointelegraph.com"
RSS_FEEDS = {
    "all": "https://cointelegraph.com/rss"  # Only use the main feed that works
}

class CointelegraphRSSCrawler:
    """Crawler for cointelegraph.com that uses RSS feeds to avoid Cloudflare protection."""
    
    def __init__(self, output_dir: str = "scraped_data", max_articles: int = 5, 
                 max_feeds: int = 2):
        """
        Initialize the crawler.
        
        Args:
            output_dir: Directory to save scraped data
            max_articles: Maximum number of articles to fetch per feed
            max_feeds: Maximum number of RSS feeds to process
        """
        self.output_dir = output_dir
        self.max_articles = max_articles
        self.max_feeds = max_feeds
        self.session = self._setup_session()
        self.visited_urls = set()
        self.results = {
            "start_time": datetime.now().isoformat(),
            "feeds_processed": 0,
            "articles_fetched": 0,
            "successful_scrapes": 0,
            "failed_scrapes": 0,
            "articles": []
        }
        
        # Create output directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_path = Path(output_dir) / timestamp
        os.makedirs(self.output_path, exist_ok=True)
    
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
    
    def wait_random(self, min_seconds=2, max_seconds=5):
        """Wait a random amount of time between requests to avoid detection."""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def fetch_rss_feed(self, feed_url: str) -> Optional[feedparser.FeedParserDict]:
        """
        Fetch and parse an RSS feed.
        
        Args:
            feed_url: URL of the RSS feed
            
        Returns:
            Parsed RSS feed or None if failed
        """
        try:
            print(f"Fetching RSS feed: {feed_url}")
            response = self.session.get(feed_url, timeout=30)
            response.raise_for_status()
            
            # Parse the feed
            feed = feedparser.parse(response.content)
            
            # Check for feed parsing errors
            if hasattr(feed, 'bozo') and feed.bozo:
                print(f"Feed parsing error for {feed_url}: {feed.bozo_exception}")
                return None
                
            if not feed.entries:
                print(f"No entries found in feed: {feed_url}")
                return None
                
            # Check if we got a valid feed structure
            if not hasattr(feed, 'feed') or not hasattr(feed.feed, 'title'):
                print(f"Invalid feed structure for {feed_url}")
                return None
                
            return feed
            
        except requests.exceptions.RequestException as e:
            print(f"Network error fetching RSS feed {feed_url}: {e}")
            return None
        except Exception as e:
            print(f"Error fetching RSS feed {feed_url}: {e}")
            return None
    
    def fetch_article_content(self, url: str) -> Optional[str]:
        """
        Fetch article content from the URL.
        
        Args:
            url: Article URL
            
        Returns:
            HTML content of the article or None if failed
        """
        try:
            print(f"Fetching article: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Check if we got a Cloudflare challenge
            if "Checking your browser" in response.text or "challenge-running" in response.text:
                print(f"Cloudflare challenge detected for {url}, skipping...")
                return None
                
            return response.text
            
        except Exception as e:
            print(f"Error fetching article {url}: {e}")
            return None
    
    def extract_article_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """
        Extract content from article HTML.
        
        Args:
            html_content: HTML content of the article
            url: URL of the article for reference
            
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
            
            # Extract title - try different selectors specific to Cointelegraph
            title_elem = (
                soup.select_one("h1.post__title") or 
                soup.select_one("h1.article__title") or
                soup.select_one("h1.main-article-title") or
                soup.select_one("h1")
            )
            if title_elem:
                article_data["title"] = title_elem.get_text().strip()
            
            # Extract date - try different selectors
            date_elem = (
                soup.select_one(".post-meta time") or
                soup.select_one(".article-meta time") or
                soup.select_one("time.datetime") or
                soup.select_one("meta[property='article:published_time']")
            )
            if date_elem:
                if date_elem.name == "meta":
                    article_data["date"] = date_elem.get("content", "")
                else:
                    article_data["date"] = date_elem.get("datetime", date_elem.get_text().strip())
            
            # Extract author - try different selectors
            author_elem = (
                soup.select_one(".post-meta__author") or
                soup.select_one(".article__author-name") or
                soup.select_one(".author-name") or
                soup.select_one("meta[name='author']")
            )
            if author_elem:
                if author_elem.name == "meta":
                    article_data["author"] = author_elem.get("content", "")
                else:
                    article_data["author"] = author_elem.get_text().strip()
            
            # Extract content - try different selectors
            content_elem = (
                soup.select_one(".post__content") or
                soup.select_one(".article__content") or
                soup.select_one(".main-article-content") or
                soup.select_one("article")
            )
            
            if content_elem:
                # Remove unwanted elements before converting to text
                for unwanted in content_elem.select(".related-articles, .advertisement, script, style, .social-share, .comments, .author-bio"):
                    unwanted.decompose()
                
                article_data["content"] = content_elem.get_text(" ", strip=True)
                article_data["markdown"] = h2t.handle(str(content_elem))
                article_data["success"] = True
            
            return article_data
            
        except Exception as e:
            print(f"Error extracting content from HTML: {e}")
            return article_data
    
    def process_feed_entry(self, entry) -> Dict[str, Any]:
        """
        Process a single feed entry (article).
        
        Args:
            entry: RSS feed entry
            
        Returns:
            Dictionary with article data
        """
        # Extract data from feed entry
        article_data = {
            "url": entry.link,
            "title": entry.title,
            "date": entry.published if hasattr(entry, "published") else "",
            "author": entry.author if hasattr(entry, "author") else "",
            "content": entry.summary if hasattr(entry, "summary") else "",
            "markdown": "",
            "success": False
        }
        
        # If the entry already has content, we could use it directly
        if hasattr(entry, "content") and entry.content:
            try:
                # Some feeds provide full content
                content_value = entry.content[0].value if isinstance(entry.content, list) else entry.content
                article_data["content"] = content_value
                article_data["markdown"] = h2t.handle(content_value)
                article_data["success"] = True
                return article_data
            except (AttributeError, IndexError):
                pass
        
        # Otherwise fetch the full article
        html_content = self.fetch_article_content(entry.link)
        if html_content:
            extracted_data = self.extract_article_content(html_content, entry.link)
            
            # If we got better data from the page, use it; otherwise keep feed data
            if extracted_data["success"]:
                article_data.update(extracted_data)
            else:
                # If we have at least the summary from the feed, mark as partially successful
                if article_data["content"]:
                    article_data["markdown"] = h2t.handle(article_data["content"])
                    article_data["success"] = True
        
        return article_data
    
    def save_article(self, article_data: Dict[str, Any]) -> str:
        """
        Save article data to files.
        
        Args:
            article_data: Dictionary containing article data
            
        Returns:
            Path to the saved markdown file
        """
        if not article_data["success"]:
            return ""
            
        try:
            # Create safe filename from title
            if not article_data["title"]:
                filename_base = str(hash(article_data["url"]))
            else:
                # Clean title to create filename
                filename_base = re.sub(r'[^\w\s-]', '', article_data["title"].lower())
                filename_base = re.sub(r'[\s-]+', '_', filename_base)
                filename_base = re.sub(r'^_+|_+$', '', filename_base)
                # Truncate if too long
                if len(filename_base) > 50:
                    filename_base = filename_base[:50]
            
            # Add timestamp to ensure uniqueness
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename_base}"
            
            # Save as markdown
            markdown_path = self.output_path / f"{filename}.md"
            
            # Create markdown content with metadata
            markdown_content = f"""# {article_data['title']}

Date: {article_data['date']}
Author: {article_data['author']}
URL: {article_data['url']}

{article_data['markdown']}
"""
            
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
                
            # Save raw JSON data
            json_path = self.output_path / f"{filename}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(article_data, f, indent=2)
                
            print(f"Saved article: {article_data['title']}")
            return str(markdown_path)
            
        except Exception as e:
            print(f"Error saving article {article_data['title']}: {e}")
            return ""
    
    def crawl(self):
        """Main crawling method."""
        try:
            # Select which feeds to process (limited by max_feeds)
            feeds_to_process = list(RSS_FEEDS.items())[:self.max_feeds]
            
            for feed_name, feed_url in feeds_to_process:
                print(f"\nProcessing feed: {feed_name} ({feed_url})")
                
                # Fetch and parse the RSS feed
                feed = self.fetch_rss_feed(feed_url)
                if not feed:
                    continue
                
                # Process entries (limited by max_articles)
                for i, entry in enumerate(feed.entries[:self.max_articles]):
                    if entry.link in self.visited_urls:
                        continue
                        
                    print(f"\nProcessing article {i+1}/{min(self.max_articles, len(feed.entries))}: {entry.title}")
                    self.visited_urls.add(entry.link)
                    
                    # Process the feed entry
                    article_data = self.process_feed_entry(entry)
                    
                    # Update statistics
                    self.results["articles_fetched"] += 1
                    if article_data["success"]:
                        self.results["successful_scrapes"] += 1
                        # Save the article
                        markdown_path = self.save_article(article_data)
                        
                        # Add to results
                        self.results["articles"].append({
                            "url": article_data["url"],
                            "title": article_data["title"],
                            "date": article_data["date"],
                            "success": True,
                            "markdown_file": markdown_path
                        })
                    else:
                        self.results["failed_scrapes"] += 1
                        self.results["articles"].append({
                            "url": article_data["url"],
                            "success": False,
                            "error": "Failed to extract content"
                        })
                    
                    # Random delay between articles
                    self.wait_random(2, 5)
                
                self.results["feeds_processed"] += 1
            
            # Save summary results
            self.results["end_time"] = datetime.now().isoformat()
            self.results["duration_seconds"] = (
                datetime.fromisoformat(self.results["end_time"]) - 
                datetime.fromisoformat(self.results["start_time"])
            ).total_seconds()
            
            summary_path = self.output_path / "summary.json"
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2)
                
            print(f"\nCrawling completed. Results saved to {self.output_path}")
            print(f"Articles fetched: {self.results['articles_fetched']}")
            print(f"Successful: {self.results['successful_scrapes']}")
            print(f"Failed: {self.results['failed_scrapes']}")
            
        except Exception as e:
            print(f"Error during crawling: {e}")

def main():
    """Parse arguments and run the crawler."""
    parser = argparse.ArgumentParser(description="Cointelegraph.com RSS Crawler")
    parser.add_argument("--output-dir", default="scraped_data", help="Directory to save scraped data")
    parser.add_argument("--max-articles", type=int, default=5, help="Maximum number of articles to fetch per feed")
    parser.add_argument("--max-feeds", type=int, default=2, help="Maximum number of RSS feeds to process")
    
    args = parser.parse_args()
    
    crawler = CointelegraphRSSCrawler(
        output_dir=args.output_dir,
        max_articles=args.max_articles,
        max_feeds=args.max_feeds
    )
    
    crawler.crawl()

if __name__ == "__main__":
    main() 