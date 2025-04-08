#!/usr/bin/env python3
"""
BeInCrypto Crawler

This script crawls BeInCrypto.com using RSS feeds, fetches articles and saves them in
both markdown and JSON formats.
"""

import os
import sys
import json
import time
import random
import re
import argparse
import datetime
import requests
from bs4 import BeautifulSoup
import html2text
import feedparser

class BeInCryptoCrawler:
    """
    A crawler for BeInCrypto.com that fetches articles from RSS feeds
    and stores them in markdown and JSON formats.
    """

    # RSS feed URL
    RSS_FEED_URL = "https://beincrypto.com/feed/"

    # User agent strings for rotating
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    ]

    def __init__(self, output_dir="scraped_data", max_articles=10):
        """
        Initialize the crawler with output directory and maximum articles to fetch.
        
        Args:
            output_dir (str): Directory where scraped articles will be saved
            max_articles (int): Maximum number of articles to fetch
        """
        self.output_dir = output_dir
        self.max_articles = max_articles
        self.session = self._setup_session()
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.body_width = 0  # No wrapping
        
        # Create a timestamp directory for this run
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = os.path.join(output_dir, timestamp)
        os.makedirs(self.run_dir, exist_ok=True)
        
        # Setup logging to file
        self.log_file = os.path.join(self.run_dir, "crawler_log.txt")
        
        self.log(f"Initialized BeInCrypto crawler. Output directory: {self.run_dir}")
        self.log(f"Max articles to fetch: {max_articles}")

    def _setup_session(self):
        """
        Set up a session with browser-like headers.
        
        Returns:
            requests.Session: Session with headers set
        """
        session = requests.Session()
        session.headers.update({
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        })
        return session

    def log(self, message):
        """
        Log a message to both console and log file.
        
        Args:
            message (str): Message to log
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        print(log_message)
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")

    def fetch_rss_feed(self):
        """
        Fetch and parse the RSS feed.
        
        Returns:
            list: List of feed entries
        """
        self.log(f"Fetching RSS feed from {self.RSS_FEED_URL}")
        
        try:
            feed = feedparser.parse(self.RSS_FEED_URL)
            
            if feed.bozo:
                self.log(f"Warning: Feed not well-formed. Error: {feed.bozo_exception}")
            
            entries = feed.entries
            self.log(f"Found {len(entries)} articles in the RSS feed")
            
            return entries
        
        except Exception as e:
            self.log(f"Error fetching RSS feed: {str(e)}")
            return []

    def fetch_article_content(self, url):
        """
        Fetch the full content of an article from its URL.
        
        Args:
            url (str): Article URL
            
        Returns:
            tuple: (BeautifulSoup object, raw HTML content) or (None, None) on failure
        """
        self.log(f"Fetching article content from: {url}")
        
        try:
            # Rotate user agent for each request
            self.session.headers.update({
                "User-Agent": random.choice(self.USER_AGENTS)
            })
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                self.log(f"Failed to fetch article. Status code: {response.status_code}")
                return None, None
            
            # Add a delay to avoid hitting rate limits
            time.sleep(random.uniform(2, 5))
            
            soup = BeautifulSoup(response.text, "html.parser")
            return soup, response.text
            
        except Exception as e:
            self.log(f"Error fetching article: {str(e)}")
            return None, None

    def extract_article_data(self, entry, soup, html_content):
        """
        Extract article data from RSS entry and HTML content.
        
        Args:
            entry (dict): RSS feed entry
            soup (BeautifulSoup): BeautifulSoup object of the article
            html_content (str): Raw HTML content
            
        Returns:
            dict: Article data or None on failure
        """
        if not soup:
            return None
        
        try:
            # Basic article data from RSS
            article_data = {
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "date_published": entry.get("published", ""),
                "author": entry.get("author", ""),
                "categories": [tag.get("term", "") for tag in entry.get("tags", [])],
                "summary": entry.get("summary", ""),
            }
            
            # Extract categories from RSS
            if "category" in entry:
                if isinstance(entry.category, list):
                    article_data["categories"] = [c for c in entry.category]
                else:
                    article_data["categories"] = [entry.category]
            
            # Get content from the RSS if it exists
            if "content" in entry and entry.content:
                content_value = entry.content[0].value
                article_data["content_html"] = content_value
                article_data["content_markdown"] = self.html_converter.handle(content_value)
                
                # Clean up the markdown content
                article_data["content_markdown"] = self.clean_markdown(article_data["content_markdown"])
            else:
                # Extract content from HTML
                article_content = soup.select_one("article") or soup.select_one(".entry-content")
                
                if not article_content:
                    # Try different selectors based on the site structure
                    article_content = soup.select_one(".post-content") or soup.select_one(".content-entry")
                
                if article_content:
                    article_data["content_html"] = str(article_content)
                    article_data["content_markdown"] = self.html_converter.handle(str(article_content))
                    
                    # Clean up the markdown content
                    article_data["content_markdown"] = self.clean_markdown(article_data["content_markdown"])
                else:
                    self.log(f"Could not extract article content from HTML")
                    article_data["content_html"] = ""
                    article_data["content_markdown"] = ""
            
            # Extract featured image
            featured_image = None
            
            # Try to find media content in the RSS entry
            if "media_content" in entry:
                featured_image = entry.media_content[0].get("url", "")
            
            # If not found in RSS, try to extract from HTML
            if not featured_image and soup:
                img_tag = soup.select_one("meta[property='og:image']")
                if img_tag:
                    featured_image = img_tag.get("content", "")
                else:
                    img_tag = soup.select_one(".featured-image img") or soup.select_one(".entry-content img")
                    if img_tag:
                        featured_image = img_tag.get("src", "")
            
            article_data["featured_image"] = featured_image or ""
            
            return article_data
            
        except Exception as e:
            self.log(f"Error extracting article data: {str(e)}")
            return None

    def clean_markdown(self, markdown_content):
        """
        Clean up the markdown content.
        
        Args:
            markdown_content (str): Markdown content to clean
            
        Returns:
            str: Cleaned markdown content
        """
        # Remove multiple consecutive newlines
        markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
        
        # Remove the "The post appeared first on BeInCrypto" footer
        markdown_content = re.sub(r'The post.*appeared first on.*BeInCrypto.*', '', markdown_content)
        
        return markdown_content.strip()

    def create_safe_filename(self, title, date):
        """
        Create a safe filename based on the article title and date.
        
        Args:
            title (str): Article title
            date (str): Article publication date
            
        Returns:
            str: Safe filename without special characters
        """
        # Replace spaces and special characters
        safe_title = re.sub(r'[^a-zA-Z0-9]', '_', title.lower())
        
        # Remove consecutive underscores
        safe_title = re.sub(r'_+', '_', safe_title)
        
        # Truncate if too long
        if len(safe_title) > 50:
            safe_title = safe_title[:50]
        
        # Add date
        try:
            # Try to parse the date
            if date:
                date_obj = datetime.datetime.strptime(date, "%a, %d %b %Y %H:%M:%S %z")
                formatted_date = date_obj.strftime("%Y%m%d_%H%M%S")
                return f"{formatted_date}_{safe_title}"
        except Exception:
            # If date parsing fails, use current datetime
            current_date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{current_date}_{safe_title}"
        
        # Fallback to current date
        current_date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{current_date}_{safe_title}"

    def save_article(self, article_data):
        """
        Save article in markdown and JSON formats.
        
        Args:
            article_data (dict): Article data
            
        Returns:
            tuple: (markdown_path, json_path) or (None, None) on failure
        """
        if not article_data:
            return None, None
        
        try:
            # Create a safe filename
            filename = self.create_safe_filename(
                article_data["title"], 
                article_data["date_published"]
            )
            
            # Save as markdown
            markdown_path = os.path.join(self.run_dir, f"{filename}.md")
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(f"# {article_data['title']}\n\n")
                f.write(f"**Author:** {article_data['author']}\n\n")
                f.write(f"**Published:** {article_data['date_published']}\n\n")
                f.write(f"**Categories:** {', '.join(article_data['categories'])}\n\n")
                
                if article_data["featured_image"]:
                    f.write(f"![Featured Image]({article_data['featured_image']})\n\n")
                
                f.write(article_data["content_markdown"])
                f.write(f"\n\nSource: [{article_data['url']}]({article_data['url']})")
            
            # Save as JSON
            json_path = os.path.join(self.run_dir, f"{filename}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(article_data, f, indent=2)
            
            self.log(f"Saved article: {article_data['title']}")
            self.log(f"  Markdown: {markdown_path}")
            self.log(f"  JSON: {json_path}")
            
            return markdown_path, json_path
            
        except Exception as e:
            self.log(f"Error saving article: {str(e)}")
            return None, None

    def process_articles(self):
        """
        Process articles from RSS feed.
        
        Returns:
            list: List of saved article paths
        """
        self.log("Starting article processing")
        
        # Fetch RSS feed
        entries = self.fetch_rss_feed()
        
        if not entries:
            self.log("No articles found in RSS feed.")
            return []
        
        # Limit to max_articles
        entries = entries[:self.max_articles]
        
        saved_articles = []
        error_count = 0
        
        for i, entry in enumerate(entries):
            self.log(f"Processing article {i+1}/{len(entries)}: {entry.get('title', 'Unknown')}")
            
            try:
                # Fetch article content
                soup, html_content = self.fetch_article_content(entry.get("link", ""))
                
                if not soup:
                    self.log(f"Skipping article due to fetch failure")
                    error_count += 1
                    continue
                
                # Extract article data
                article_data = self.extract_article_data(entry, soup, html_content)
                
                if not article_data:
                    self.log(f"Skipping article due to data extraction failure")
                    error_count += 1
                    continue
                
                # Save article
                markdown_path, json_path = self.save_article(article_data)
                
                if markdown_path and json_path:
                    saved_articles.append((markdown_path, json_path))
                else:
                    error_count += 1
                
            except Exception as e:
                self.log(f"Error processing article: {str(e)}")
                error_count += 1
                continue
            
            # Add a delay between articles
            if i < len(entries) - 1:
                delay = random.uniform(2, 5)
                self.log(f"Waiting {delay:.2f} seconds before next article...")
                time.sleep(delay)
        
        # Generate summary
        self.log("Article processing completed!")
        self.log(f"Successfully saved: {len(saved_articles)}/{len(entries)} articles")
        self.log(f"Errors: {error_count}/{len(entries)} articles")
        
        # Write summary to file
        summary_path = os.path.join(self.run_dir, "summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            summary = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_articles": len(entries),
                "saved_articles": len(saved_articles),
                "errors": error_count,
                "article_files": [
                    {
                        "markdown": os.path.basename(md),
                        "json": os.path.basename(js)
                    } for md, js in saved_articles
                ]
            }
            json.dump(summary, f, indent=2)
        
        return saved_articles

def main():
    """
    Main function to run the crawler.
    """
    parser = argparse.ArgumentParser(description="BeInCrypto Crawler")
    
    parser.add_argument(
        "-a", "--articles",
        type=int,
        default=10,
        help="Maximum number of articles to fetch (default: 10)"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="scraped_data",
        help="Output directory for scraped data (default: scraped_data)"
    )
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Run the crawler
    crawler = BeInCryptoCrawler(
        output_dir=args.output,
        max_articles=args.articles
    )
    
    crawler.process_articles()

if __name__ == "__main__":
    main() 