#!/usr/bin/env python3
"""
Cryptonews.com Crawler

This script crawls cryptonews.com website to scrape cryptocurrency news articles.
It uses Selenium with undetected-chromedriver to bypass Cloudflare protection.
"""

import os
import sys
import json
import time
import random
import re
import argparse
from datetime import datetime
from urllib.parse import urljoin, urlparse
from pathlib import Path
import html2text
from typing import List, Dict, Any, Tuple, Optional

try:
    import undetected_chromedriver as uc
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from bs4 import BeautifulSoup
except ImportError:
    print("Required packages not found. Installing...")
    os.system("pip install undetected-chromedriver selenium beautifulsoup4 html2text")
    import undetected_chromedriver as uc
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from bs4 import BeautifulSoup

# Configure HTML to Text converter
h2t = html2text.HTML2Text()
h2t.ignore_links = False
h2t.ignore_images = True
h2t.ignore_tables = True
h2t.ignore_emphasis = True
h2t.body_width = 0  # No wrapping

# Base URL and sections to crawl
BASE_URL = "https://cryptonews.com"
DEFAULT_SECTIONS = [
    "/news/",
    "/exclusives/",
    "/opinions/",
    "/guides/",
]

class CryptonewsCrawler:
    """Crawler for cryptonews.com that bypasses Cloudflare protection."""
    
    def __init__(self, output_dir: str = "scraped_data", max_articles: int = 5, 
                 max_sections: int = 3, headless: bool = True):
        """
        Initialize the crawler.
        
        Args:
            output_dir: Directory to save scraped data
            max_articles: Maximum number of articles to scrape per section
            max_sections: Maximum number of sections to scrape
            headless: Whether to run Chrome in headless mode
        """
        self.output_dir = output_dir
        self.max_articles = max_articles
        self.max_sections = max_sections
        self.headless = headless
        self.driver = None
        self.visited_urls = set()
        self.results = {
            "start_time": datetime.now().isoformat(),
            "sections_crawled": 0,
            "articles_scraped": 0,
            "successful_scrapes": 0,
            "failed_scrapes": 0,
            "articles": []
        }
        
        # Create output directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_path = Path(output_dir) / timestamp
        os.makedirs(self.output_path, exist_ok=True)
        
    def setup_driver(self):
        """Set up and configure the undetected Chrome driver."""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        
        # Set user agent to appear more like a regular browser
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        try:
            self.driver = uc.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
            print("Browser initialized successfully")
        except Exception as e:
            print(f"Failed to initialize browser: {e}")
            sys.exit(1)
    
    def close_driver(self):
        """Close the browser driver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def wait_random(self, min_seconds=2, max_seconds=5):
        """Wait a random amount of time between requests to avoid detection."""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def get_page_with_retry(self, url: str, max_retries: int = 3) -> bool:
        """
        Load a page with retry logic.
        
        Args:
            url: URL to load
            max_retries: Maximum number of retries
            
        Returns:
            bool: True if page loaded successfully, False otherwise
        """
        if not self.driver:
            self.setup_driver()
            
        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                
                # Wait for page to load (wait for the main content)
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Check if we're blocked by Cloudflare
                if "Checking your browser" in self.driver.page_source or "challenge-running" in self.driver.page_source:
                    print(f"Detected Cloudflare challenge, waiting longer... (attempt {attempt + 1})")
                    # Wait up to 20 seconds for Cloudflare to resolve
                    time.sleep(20)
                    continue
                    
                # Check if we have content
                if len(self.driver.page_source) < 1000:
                    print(f"Page content too small, might be blocked. Retrying... (attempt {attempt + 1})")
                    time.sleep(5)
                    continue
                    
                return True
                
            except TimeoutException:
                print(f"Timeout loading {url}. Retrying... (attempt {attempt + 1})")
                time.sleep(5)
            except Exception as e:
                print(f"Error loading {url}: {e}. Retrying... (attempt {attempt + 1})")
                time.sleep(5)
                
        print(f"Failed to load {url} after {max_retries} attempts")
        return False
    
    def extract_article_links(self, section_url: str) -> List[str]:
        """
        Extract article links from a section page.
        
        Args:
            section_url: URL of the section to extract links from
            
        Returns:
            List of article URLs
        """
        article_links = []
        
        if not self.get_page_with_retry(section_url):
            return article_links
            
        try:
            # Save page content for debugging
            with open("page_content.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
                
            # Parse the page with BeautifulSoup for better link extraction
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            
            # Debug: Print total number of links found
            all_links = soup.find_all("a", href=True)
            print(f"Found {len(all_links)} total links on {section_url}")
            
            # Look for article containers - cryptonews.com typically has news items in containers
            article_containers = soup.select(".cn-tile") or soup.select(".cn-news-bg") or soup.select(".cn-img-article")
            
            for container in article_containers:
                link_elem = container.find("a", href=True)
                if not link_elem:
                    continue
                    
                href = link_elem["href"]
                
                # Make sure it's an absolute URL
                if href.startswith("/"):
                    full_url = urljoin(BASE_URL, href)
                else:
                    full_url = href
                    
                # Skip if not from cryptonews.com or already visited
                if "cryptonews.com" not in full_url or full_url in self.visited_urls:
                    continue
                    
                article_links.append(full_url)
                self.visited_urls.add(full_url)
                
                if len(article_links) >= self.max_articles:
                    break
                    
            # If no articles found through containers, try a more generic approach
            if not article_links:
                print("No articles found via containers, trying generic approach")
                for link in all_links:
                    href = link["href"]
                    
                    # Check if it looks like an article URL (cryptonews.com article patterns)
                    if (href.startswith("/news/") or href.startswith("/exclusives/") or 
                        href.startswith("/guides/") or href.startswith("/opinions/")):
                        
                        full_url = urljoin(BASE_URL, href)
                        
                        if full_url not in self.visited_urls:
                            article_links.append(full_url)
                            self.visited_urls.add(full_url)
                            
                            if len(article_links) >= self.max_articles:
                                break
            
            print(f"Found {len(article_links)} article links from {section_url}")
            return article_links
            
        except Exception as e:
            print(f"Error extracting article links from {section_url}: {e}")
            return article_links
    
    def extract_article_content(self, url: str) -> Dict[str, Any]:
        """
        Extract content from an article page.
        
        Args:
            url: URL of the article
            
        Returns:
            Dictionary containing article data
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
        
        if not self.get_page_with_retry(url):
            return article_data
            
        try:
            # Parse the article page with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            
            # Extract title
            title_elem = (
                soup.select_one("h1.mb-3") or 
                soup.select_one("h1.article__title") or
                soup.select_one("h1")
            )
            if title_elem:
                article_data["title"] = title_elem.get_text().strip()
            
            # Extract date
            date_elem = (
                soup.select_one("time") or
                soup.select_one(".article__date") or
                soup.select_one(".date") or
                soup.select_one("meta[property='article:published_time']")
            )
            if date_elem:
                if date_elem.name == "meta":
                    article_data["date"] = date_elem.get("content", "")
                else:
                    article_data["date"] = date_elem.get_text().strip()
            
            # Extract author
            author_elem = (
                soup.select_one(".article__author") or
                soup.select_one(".author") or
                soup.select_one("meta[name='author']")
            )
            if author_elem:
                if author_elem.name == "meta":
                    article_data["author"] = author_elem.get("content", "")
                else:
                    article_data["author"] = author_elem.get_text().strip()
            
            # Extract content
            content_elem = (
                soup.select_one(".article__body") or
                soup.select_one(".cn-content") or
                soup.select_one("article") or
                soup.select_one(".post-content")
            )
            
            if content_elem:
                # Remove unwanted elements before converting to text
                for unwanted in content_elem.select(".cn-related-articles, .cn-advertisement, .cn-cta, script, style"):
                    unwanted.decompose()
                
                article_data["content"] = content_elem.get_text(" ", strip=True)
                article_data["markdown"] = h2t.handle(str(content_elem))
                article_data["success"] = True
            
            return article_data
            
        except Exception as e:
            print(f"Error extracting content from {url}: {e}")
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
            self.setup_driver()
            
            # Get sections to crawl (limited by max_sections)
            sections_to_crawl = DEFAULT_SECTIONS[:self.max_sections]
            
            for section in sections_to_crawl:
                section_url = urljoin(BASE_URL, section)
                print(f"\nCrawling section: {section_url}")
                
                # Extract article links from this section
                article_links = self.extract_article_links(section_url)
                
                # Process each article
                for article_url in article_links:
                    print(f"\nProcessing article: {article_url}")
                    
                    # Extract article content
                    article_data = self.extract_article_content(article_url)
                    
                    # Update statistics
                    self.results["articles_scraped"] += 1
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
                    self.wait_random(3, 7)
                
                self.results["sections_crawled"] += 1
            
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
            print(f"Articles scraped: {self.results['articles_scraped']}")
            print(f"Successful: {self.results['successful_scrapes']}")
            print(f"Failed: {self.results['failed_scrapes']}")
            
        except Exception as e:
            print(f"Error during crawling: {e}")
        finally:
            self.close_driver()

def main():
    """Parse arguments and run the crawler."""
    parser = argparse.ArgumentParser(description="Cryptonews.com Crawler")
    parser.add_argument("--output-dir", default="scraped_data", help="Directory to save scraped data")
    parser.add_argument("--max-articles", type=int, default=5, help="Maximum number of articles to scrape per section")
    parser.add_argument("--max-sections", type=int, default=3, help="Maximum number of sections to scrape")
    parser.add_argument("--no-headless", action="store_true", help="Run Chrome in visible mode")
    
    args = parser.parse_args()
    
    crawler = CryptonewsCrawler(
        output_dir=args.output_dir,
        max_articles=args.max_articles,
        max_sections=args.max_sections,
        headless=not args.no_headless
    )
    
    crawler.crawl()

if __name__ == "__main__":
    main() 