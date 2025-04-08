#!/usr/bin/env python3
"""
Bitcoin.com News Crawler with Selenium

This script crawls the Bitcoin.com news RSS feed to fetch cryptocurrency news articles
and uses Selenium to render JavaScript for full article content extraction.
Saves articles in markdown and JSON formats.
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
from bs4 import BeautifulSoup
import html2text
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configure HTML to Text converter
h2t = html2text.HTML2Text()
h2t.ignore_links = False
h2t.ignore_images = False
h2t.ignore_tables = False
h2t.ignore_emphasis = False
h2t.body_width = 0  # No wrapping

# List of RSS feeds to crawl
RSS_FEEDS = {
    "main": "https://news.bitcoin.com/feed/",
}

class BitcoinComSeleniumCrawler:
    """Crawler for Bitcoin.com news articles using Selenium for full content extraction."""
    
    def __init__(self, output_dir="scraped_data", max_articles=10, max_feeds=None, headless=True):
        """
        Initialize the crawler.
        
        Args:
            output_dir (str): Directory to save the scraped data
            max_articles (int): Maximum number of articles to fetch per feed
            max_feeds (int): Maximum number of feeds to process
            headless (bool): Whether to run the browser in headless mode
        """
        self.output_dir = output_dir
        self.max_articles = max_articles
        self.max_feeds = max_feeds
        self.headless = headless
        self.session = self._setup_session()
        self.driver = self._setup_selenium_driver()
        
        # Create a timestamped directory for this crawl
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(output_dir, timestamp)
        os.makedirs(self.output_dir, exist_ok=True)
        
        print(f"Output directory: {self.output_dir}")
    
    def _setup_session(self):
        """Set up a session with browser-like headers."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        return session
    
    def _setup_selenium_driver(self):
        """Set up and return a Selenium WebDriver."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            print(f"Error setting up Selenium WebDriver: {e}")
            print("Make sure you have installed Chrome browser and chromedriver.")
            sys.exit(1)
    
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
    
    def _wait(self, min_seconds=1, max_seconds=3):
        """Wait for a random time between requests to avoid overloading the server."""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def fetch_rss_feed(self, feed_url):
        """
        Fetch and parse an RSS feed.
        
        Args:
            feed_url (str): URL of the RSS feed
            
        Returns:
            feedparser.FeedParserDict: Parsed feed or None if failed
        """
        try:
            response = self.session.get(feed_url, timeout=10)
            response.raise_for_status()
            
            # Parse the feed content
            feed = feedparser.parse(response.content)
            if not feed.entries:
                print(f"Warning: No entries found in feed {feed_url}")
                return None
                
            return feed
        except requests.exceptions.RequestException as e:
            print(f"Network error fetching feed {feed_url}: {e}")
            return None
        except Exception as e:
            print(f"Error parsing feed {feed_url}: {e}")
            return None
    
    def fetch_article_content_with_selenium(self, url):
        """
        Fetch article content using Selenium to render JavaScript.
        
        Args:
            url (str): URL of the article
            
        Returns:
            tuple: (rendered_html, article_content_html, article_title)
        """
        try:
            print(f"Loading article with Selenium: {url}")
            self.driver.get(url)
            
            # Wait for content to load
            wait = WebDriverWait(self.driver, 20)
            
            # Wait for the main content elements to be visible
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .article__title, .article-header, .post-title")))
                print("Title found, page loaded")
            except TimeoutException:
                print("Timeout waiting for article title to load")
            
            # Give extra time for the rest of the content to render
            self._wait(3, 5)
            
            # Get the page title
            article_title = ""
            try:
                title_element = self.driver.find_element(By.CSS_SELECTOR, "h1, .article__title, .article-header, .post-title")
                if title_element:
                    article_title = title_element.text
            except Exception as e:
                print(f"Error extracting title: {e}")
            
            # Get the rendered HTML
            rendered_html = self.driver.page_source
            
            # Extract article content using various selectors
            article_content_html = ""
            for selector in [".article-content", ".article__body", ".entry-content", "article .post-content", ".post-entry", ".content-article"]:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element:
                        article_content_html = element.get_attribute('outerHTML')
                        print(f"Found article content using selector: {selector}")
                        break
                except Exception:
                    continue
            
            return rendered_html, article_content_html, article_title
            
        except WebDriverException as e:
            print(f"Selenium error loading {url}: {e}")
            return None, None, None
        except Exception as e:
            print(f"Error in fetch_article_content_with_selenium for {url}: {e}")
            return None, None, None
    
    def extract_article_data(self, entry, rendered_html, article_content_html, article_title):
        """
        Extract article data from RSS entry and HTML content.
        
        Args:
            entry (dict): RSS feed entry
            rendered_html (str): Full rendered HTML from Selenium
            article_content_html (str): HTML of the article content section
            article_title (str): Title extracted from Selenium
            
        Returns:
            dict: Extracted article data
        """
        # Parse HTML content
        soup = BeautifulSoup(rendered_html, 'html.parser')
        
        # Extract title (prefer Selenium extracted title if available)
        title = article_title if article_title else entry.get('title', '')
        
        # Extract publication date
        pub_date = entry.get('published', '')
        if pub_date:
            try:
                # Convert to ISO format
                dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z')
                pub_date = dt.isoformat()
            except (ValueError, TypeError):
                pass
        
        # Extract author
        author = entry.get('author', '')
        if not author and 'dc_creator' in entry:
            author = entry.get('dc_creator', '')
        
        # If author still not found, try to extract from the rendered page
        if not author:
            try:
                author_element = soup.select_one('meta[name="author"]')
                if author_element and author_element.get('content'):
                    author = author_element.get('content')
            except Exception:
                pass
        
        # Extract description/summary from RSS
        description = ""
        if hasattr(entry, 'summary'):
            description = entry.summary
        elif 'description' in entry:
            description = entry.description
        
        # Clean description from HTML
        if description:
            description_soup = BeautifulSoup(description, 'html.parser')
            description = description_soup.get_text()
        
        # Process article content
        article_content = ""
        if article_content_html:
            # Parse the article content HTML
            content_soup = BeautifulSoup(article_content_html, 'html.parser')
            
            # Remove any unwanted elements
            for unwanted in content_soup.select('.social-share, .ad-container, .newsletter-container, .article__share, script, iframe, .share-buttons, .related-posts'):
                unwanted.decompose()
            
            article_content = str(content_soup)
        
        # If no article content found, try to find it in the full rendered HTML
        if not article_content:
            for selector in [".article-content", ".article__body", ".entry-content", "article .post-content", ".post-entry", ".content-article"]:
                content_element = soup.select_one(selector)
                if content_element:
                    # Remove any unwanted elements
                    for unwanted in content_element.select('.social-share, .ad-container, .newsletter-container, .article__share, script, iframe, .share-buttons, .related-posts'):
                        unwanted.decompose()
                    
                    article_content = str(content_element)
                    break
        
        # Convert HTML content to markdown
        markdown_content = h2t.handle(article_content) if article_content else ""
        
        # If markdown content is still empty, use the description
        if not markdown_content.strip() and description:
            markdown_content = "**Note: Full article content could not be retrieved. Below is a summary from the RSS feed.**\n\n" + description
        
        # Extract categories/tags
        categories = [tag.get('term') for tag in entry.get('tags', [])] if hasattr(entry, 'tags') else []
        
        # Create clean filename from title
        filename = self.create_safe_filename(title)
        
        # Extract thumbnail image URL
        thumbnail_url = ""
        
        # First try to get it from the RSS feed
        if 'media_thumbnail' in entry and entry.media_thumbnail:
            thumbnail_url = entry.media_thumbnail[0].get('url', '')
        elif hasattr(entry, 'bnmedia_post-thumbnail'):
            try:
                thumbnail_url = getattr(entry, 'bnmedia_post-thumbnail').bnmedia_url
            except (AttributeError, KeyError):
                pass
        
        # If not found, try to extract from the rendered page
        if not thumbnail_url:
            try:
                # Look for og:image
                og_image = soup.select_one('meta[property="og:image"]')
                if og_image and og_image.get('content'):
                    thumbnail_url = og_image.get('content')
            except Exception:
                pass
        
        # If still not found, try to extract from the description
        if not thumbnail_url and hasattr(entry, 'summary'):
            summary_soup = BeautifulSoup(entry.summary, 'html.parser')
            img = summary_soup.find('img')
            if img and img.get('src'):
                thumbnail_url = img['src']
        
        # Extract meta information from HTML if possible
        meta_description = ""
        try:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                meta_description = meta_desc.get('content')
        except Exception:
            pass
        
        return {
            'title': title,
            'url': entry.get('link', ''),
            'publication_date': pub_date,
            'author': author,
            'content': markdown_content,
            'html_content': article_content,
            'summary': description,
            'meta_description': meta_description,
            'categories': categories,
            'thumbnail_url': thumbnail_url,
            'filename': filename,
        }
    
    def create_safe_filename(self, title):
        """
        Create a safe filename from the article title.
        
        Args:
            title (str): Article title
            
        Returns:
            str: Safe filename
        """
        # Replace special characters with underscores
        safe_title = re.sub(r'[^\w\s-]', '', title.lower())
        safe_title = re.sub(r'[\s-]+', '_', safe_title)
        
        # Truncate to avoid excessively long filenames
        if len(safe_title) > 50:
            safe_title = safe_title[:50]
        
        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{safe_title}"
    
    def process_feed_entries(self, feed, feed_name):
        """
        Process entries from a feed.
        
        Args:
            feed (feedparser.FeedParserDict): Parsed feed
            feed_name (str): Name of the feed
            
        Returns:
            int: Number of articles processed
        """
        if not feed or not feed.entries:
            print(f"No entries found in feed: {feed_name}")
            return 0
        
        print(f"Processing feed: {feed_name} ({len(feed.entries)} entries)")
        
        # Limit the number of articles to process
        entries = feed.entries[:self.max_articles]
        processed_count = 0
        
        for entry in entries:
            # Get article URL
            url = entry.get('link')
            if not url:
                print("Skipping entry without URL")
                continue
            
            print(f"Fetching article: {url}")
            
            # Fetch article content with Selenium
            rendered_html, article_content_html, article_title = self.fetch_article_content_with_selenium(url)
            
            if not rendered_html:
                print(f"Failed to fetch article content with Selenium: {url}")
                continue
            
            # Extract article data
            article_data = self.extract_article_data(entry, rendered_html, article_content_html, article_title)
            
            # Save the article
            self.save_article(article_data)
            
            processed_count += 1
            print(f"Processed article {processed_count}/{len(entries)}: {article_data['title']}")
            
            # Wait before next request
            if processed_count < len(entries):
                self._wait(2, 4)
        
        return processed_count
    
    def save_article(self, article_data):
        """
        Save article data as markdown and JSON.
        
        Args:
            article_data (dict): Article data to save
        """
        # Create filename
        filename = article_data['filename']
        
        # Save as markdown
        markdown_path = os.path.join(self.output_dir, f"{filename}.md")
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(f"# {article_data['title']}\n\n")
            f.write(f"**Source:** [{article_data['url']}]({article_data['url']})\n\n")
            f.write(f"**Publication Date:** {article_data['publication_date']}\n\n")
            f.write(f"**Author:** {article_data['author']}\n\n")
            
            if article_data['categories']:
                f.write(f"**Categories:** {', '.join(article_data['categories'])}\n\n")
            
            if article_data['thumbnail_url']:
                f.write(f"![Thumbnail]({article_data['thumbnail_url']})\n\n")
            
            if article_data['summary']:
                f.write(f"## Summary\n\n{article_data['summary']}\n\n")
            
            f.write(f"## Content\n\n{article_data['content']}\n")
        
        # Save as JSON
        json_path = os.path.join(self.output_dir, f"{filename}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(article_data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved article to {markdown_path}")
    
    def run(self):
        """Execute the crawling process."""
        print(f"Starting Bitcoin.com news crawler with Selenium. Max articles per feed: {self.max_articles}")
        
        total_processed = 0
        feed_count = 0
        
        for feed_name, feed_url in RSS_FEEDS.items():
            if self.max_feeds is not None and feed_count >= self.max_feeds:
                break
            
            print(f"Fetching feed: {feed_name} ({feed_url})")
            feed = self.fetch_rss_feed(feed_url)
            
            if feed:
                articles_processed = self.process_feed_entries(feed, feed_name)
                total_processed += articles_processed
                feed_count += 1
                
                print(f"Processed {articles_processed} articles from feed: {feed_name}")
                
                # Wait before fetching the next feed
                if feed_count < len(RSS_FEEDS) and (self.max_feeds is None or feed_count < self.max_feeds):
                    self._wait(3, 5)
        
        print(f"Crawling completed! Processed {total_processed} articles from {feed_count} feeds.")
        
        # Quit the Selenium driver
        try:
            self.driver.quit()
            print("Selenium browser closed.")
        except Exception as e:
            print(f"Error closing Selenium browser: {e}")
        
        return total_processed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Bitcoin.com News Crawler with Selenium')
    parser.add_argument('-o', '--output', type=str, default='scraped_data',
                        help='Output directory for scraped data')
    parser.add_argument('-a', '--articles', type=int, default=10,
                        help='Maximum number of articles to fetch per feed')
    parser.add_argument('-f', '--feeds', type=int, default=None,
                        help='Maximum number of feeds to process')
    parser.add_argument('--no-headless', action='store_true',
                        help='Run browser in non-headless mode (visible)')
    
    args = parser.parse_args()
    
    # Create the crawler and run it
    crawler = BitcoinComSeleniumCrawler(
        output_dir=args.output,
        max_articles=args.articles,
        max_feeds=args.feeds,
        headless=not args.no_headless
    )
    
    crawler.run()


if __name__ == "__main__":
    main() 