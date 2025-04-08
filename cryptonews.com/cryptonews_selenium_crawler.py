#!/usr/bin/env python3
"""
CryptoNews.com Selenium Crawler

This script crawls cryptonews.com website to scrape cryptocurrency news articles.
It uses Selenium with undetected-chromedriver to bypass Cloudflare protection and
implements robust error handling and article extraction.
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
from typing import List, Dict, Any, Tuple, Optional, Set
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

try:
    import undetected_chromedriver as uc
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
    from bs4 import BeautifulSoup
except ImportError:
    logger.info("Required packages not found. Installing...")
    os.system("pip install undetected-chromedriver selenium beautifulsoup4 html2text")
    import undetected_chromedriver as uc
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
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
    "/",  # Homepage
    "/news/",
    "/exclusives/",
    "/opinions/",
    "/guides/",
    "/bitcoin-news/",
    "/ethereum-news/",
    "/nft-news/",
    "/altcoin-news/",
]

class CryptoNewsSeleniumCrawler:
    """Advanced crawler for CryptoNews.com that bypasses Cloudflare protection."""
    
    def __init__(self, output_dir: str = "scraped_data", max_articles: int = 5, 
                 max_sections: int = 3, headless: bool = True, max_retries: int = 3):
        """
        Initialize the crawler.
        
        Args:
            output_dir: Directory to save scraped data
            max_articles: Maximum number of articles to scrape per section
            max_sections: Maximum number of sections to scrape
            headless: Whether to run Chrome in headless mode
            max_retries: Maximum number of retries for failed requests
        """
        self.output_dir = output_dir
        self.max_articles = max_articles
        self.max_sections = max_sections
        self.headless = headless
        self.max_retries = max_retries
        self.driver = None
        self.visited_urls: Set[str] = set()
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
        """Set up and configure the undetected Chrome driver with optimal settings."""
        try:
            options = webdriver.ChromeOptions()
            
            if self.headless:
                options.add_argument("--headless=new")
            
            # Essential options for avoiding detection
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--start-maximized")
            
            # Set user agent to appear more like a regular browser
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
            
            # Add language preferences
            options.add_argument("--lang=en-US")
            
            # Do NOT use experimental options with undetected_chromedriver
            # as they cause compatibility issues
            
            # Create and configure the driver
            self.driver = uc.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
            
            # Execute script to avoid detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Browser initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            return False
    
    def close_driver(self):
        """Close the browser driver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Browser closed")
    
    def wait_random(self, min_seconds=2, max_seconds=5):
        """Wait a random amount of time between requests to avoid detection."""
        wait_time = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Waiting {wait_time:.2f} seconds...")
        time.sleep(wait_time)
    
    def get_page_with_retry(self, url: str) -> bool:
        """
        Load a page with retry logic to handle Cloudflare and other issues.
        
        Args:
            url: URL to load
            
        Returns:
            bool: True if page loaded successfully, False otherwise
        """
        if not self.driver and not self.setup_driver():
            return False
            
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Loading page {url} (attempt {attempt + 1}/{self.max_retries})")
                self.driver.get(url)
                
                # Wait for page to load (wait for the main content)
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Check if we're blocked by Cloudflare
                if "Checking your browser" in self.driver.page_source or "challenge-running" in self.driver.page_source:
                    logger.warning(f"Detected Cloudflare challenge, waiting longer... (attempt {attempt + 1})")
                    # Wait up to 20 seconds for Cloudflare to resolve
                    time.sleep(20)
                    continue
                    
                # Check if we have content
                if len(self.driver.page_source) < 1000:
                    logger.warning(f"Page content too small, might be blocked. Retrying... (attempt {attempt + 1})")
                    time.sleep(5)
                    continue
                
                # Check for specific page elements to confirm successful load
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "header, .header, #header, .nav, nav"))
                    )
                    logger.info(f"Page loaded successfully: {url}")
                    return True
                except TimeoutException:
                    logger.warning(f"Could not find key page elements. Page might not have loaded correctly.")
                    if attempt < self.max_retries - 1:
                        time.sleep(5)
                        continue
                    
            except TimeoutException:
                logger.warning(f"Timeout loading {url}. Retrying... (attempt {attempt + 1})")
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error loading {url}: {e}. Retrying... (attempt {attempt + 1})")
                time.sleep(5)
                
        logger.error(f"Failed to load {url} after {self.max_retries} attempts")
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
            # Parse the page with BeautifulSoup for better link extraction
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            
            # Debug: Save the page source for inspection if in debug mode
            if logger.level <= logging.DEBUG:
                debug_file = f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                logger.debug(f"Saved page source to {debug_file} for debugging")
            
            # Check which selectors are present and their counts
            selectors_to_try = [
                ".aside-news-top", 
                ".homepage-block__partnered-articles-single",
                ".articles-for-you-block__item",
                ".top-section-new__column-article",
                ".top-section-new__right-item",
                ".article-box",
                ".news-item",
                ".post",
                ".article"
            ]
            
            selector_counts = {}
            for selector in selectors_to_try:
                elements = soup.select(selector)
                selector_counts[selector] = len(elements)
                logger.info(f"Selector '{selector}' found {len(elements)} elements")
            
            # Process .aside-news-top elements (sidebar news)
            for container in soup.select(".aside-news-top")[:self.max_articles]:
                link_element = container.select_one(".aside-news-top__title a")
                if not link_element:
                    link_element = container.select_one("a")
                    
                if link_element and link_element.has_attr("href"):
                    href = link_element["href"]
                    # Make absolute URL if needed
                    if href.startswith("/"):
                        article_url = urljoin(BASE_URL, href)
                    elif href.startswith("http"):
                        article_url = href
                    else:
                        continue
                        
                    # Only add CryptoNews.com URLs and skip blacklisted paths
                    if self._is_valid_article_url(article_url):
                        article_links.append(article_url)
                        self.visited_urls.add(article_url)
                        logger.info(f"Added article (aside-news-top): {article_url}")
                        
                        if len(article_links) >= self.max_articles:
                            break
            
            # If we need more articles, process partnered articles
            if len(article_links) < self.max_articles:
                for container in soup.select(".homepage-block__partnered-articles-single")[:self.max_articles]:
                    link_element = container.select_one(".homepage-block__partnered-articles-single-link")
                    if not link_element:
                        link_element = container.select_one("a")
                        
                    if link_element and link_element.has_attr("href"):
                        href = link_element["href"]
                        # Make absolute URL if needed
                        if href.startswith("/"):
                            article_url = urljoin(BASE_URL, href)
                        elif href.startswith("http"):
                            article_url = href
                        else:
                            continue
                            
                        # Only add CryptoNews.com URLs and skip blacklisted paths
                        if self._is_valid_article_url(article_url):
                            article_links.append(article_url)
                            self.visited_urls.add(article_url)
                            logger.info(f"Added article (partnered): {article_url}")
                            
                            if len(article_links) >= self.max_articles:
                                break
            
            # If we still need more articles, look more broadly
            if len(article_links) < self.max_articles:
                logger.info("Looking for additional article links in all links")
                all_links = soup.find_all("a", href=True)
                
                # Extract all article-looking links
                for link in all_links:
                    href = link.get("href", "")
                    
                    # Skip already processed links
                    if href.startswith("/"):
                        article_url = urljoin(BASE_URL, href)
                    elif href.startswith("http"):
                        article_url = href
                    else:
                        continue
                    
                    # Skip if already in our list
                    if article_url in self.visited_urls:
                        continue
                        
                    # Check if it's a valid article URL
                    if self._is_valid_article_url(article_url):
                        # Check if the link has text and looks like an article title
                        link_text = link.get_text().strip()
                        if link_text and len(link_text) > 15 and len(link_text.split()) > 3:
                            article_links.append(article_url)
                            self.visited_urls.add(article_url)
                            logger.info(f"Added article from general links: {article_url}")
                            
                            if len(article_links) >= self.max_articles:
                                break
            
            logger.info(f"Extracted {len(article_links)} article links from {section_url}")
            return article_links
            
        except Exception as e:
            logger.error(f"Error extracting article links from {section_url}: {e}")
            return article_links
    
    def _is_valid_article_url(self, url: str) -> bool:
        """
        Check if a URL is a valid article URL.
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if valid article URL, False otherwise
        """
        # Must be a cryptonews.com URL
        if "cryptonews.com" not in url:
            return False
            
        # Skip redirect/outgoing URLs
        if "rapi.cryptonews.com/outgoing" in url:
            return False
            
        # Skip obvious non-article paths
        skip_paths = [
            "/coins/", 
            "/about/", 
            "/advertise/", 
            "/terms/", 
            "/privacy/",
            "/feed/",
            "/tag/",
            "/?",
            "/page/",
            "/author/"
        ]
        
        if any(path in url for path in skip_paths):
            return False
            
        # Skip anchor links
        if "#" in url:
            return False
            
        # Skip external sites
        if "ext/" in url and not url.endswith("/?transfer=1"):
            return False
            
        # Must have at least 2 path segments to be an article
        path = urlparse(url).path.strip("/")
        if path.count("/") < 1:
            return False
            
        return True
    
    def extract_article_content(self, url: str) -> Dict[str, Any]:
        """
        Extract content from an article page.
        
        Args:
            url: URL of the article
            
        Returns:
            Dictionary with extracted article data
        """
        article_data = {
            "url": url,
            "title": "",
            "date": "",
            "author": "",
            "tags": [],
            "content": "",
            "markdown": "",
            "summary": "",
            "success": False
        }
        
        if not self.get_page_with_retry(url):
            return article_data
        
        try:
            # Parse with BeautifulSoup for better extraction
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Debug: Save the article HTML if in debug mode
            if logger.level <= logging.DEBUG:
                article_id = url.rstrip('/').split('/')[-1]
                debug_file = f"article_{article_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.debug(f"Saved article HTML to {debug_file} for debugging")
            
            # Extract title - try different selectors specific to CryptoNews.com
            title_elem = (
                soup.select_one("h1.post-title") or 
                soup.select_one("h1.entry-title") or
                soup.select_one("h1.article-title") or
                soup.select_one("h1.single-post__title") or
                soup.select_one("h1.page-title") or
                soup.select_one("h1.mb-3") or 
                soup.select_one("h1.article__title") or
                soup.select_one("h1")
            )
            if title_elem:
                article_data["title"] = title_elem.get_text().strip()
                logger.info(f"Found article title: {article_data['title']}")
            
            # Extract date - try different selectors
            date_elem = (
                soup.select_one(".post-date") or
                soup.select_one(".date-published") or
                soup.select_one(".single-post__date") or
                soup.select_one(".publish-date") or
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
                logger.info(f"Found article date: {article_data['date']}")
            
            # Extract author - try different selectors
            author_elem = (
                soup.select_one(".author") or
                soup.select_one(".post-author") or
                soup.select_one(".article-author") or
                soup.select_one(".single-post__author") or
                soup.select_one(".article__author") or
                soup.select_one("meta[name='author']") or
                soup.select_one("a[rel='author']")
            )
            if author_elem:
                if author_elem.name == "meta":
                    article_data["author"] = author_elem.get("content", "")
                else:
                    article_data["author"] = author_elem.get_text().strip()
                logger.info(f"Found article author: {article_data['author']}")
            
            # Extract tags/categories
            tag_elems = soup.select(".tags a, .categories a, .post-tags a, .article-tags a, .single-post__tags-list a")
            article_data["tags"] = [tag.get_text().strip() for tag in tag_elems]
            if article_data["tags"]:
                logger.info(f"Found {len(article_data['tags'])} article tags")
            
            # Special handling for reports section
            if "/reports/" in url:
                logger.info("Detected 'reports' type article, using special extraction")
                
                # Reports have content in special elements
                report_content = None
                
                # Try different structures for report content
                report_content_selectors = [
                    ".single-post__body",
                    ".single-post__content",
                    ".report-content",
                    ".entry-content"
                ]
                
                for selector in report_content_selectors:
                    report_content = soup.select_one(selector)
                    if report_content:
                        logger.info(f"Found report content using selector: {selector}")
                        break
                
                # If we still don't have content, try to extract content from the main article
                if not report_content:
                    main_content = soup.select_one("main") or soup.select_one("article")
                    if main_content:
                        # Clean up the content - remove headers, footers, menus
                        for unwanted in main_content.select("header, nav, footer, aside, .sidebar, .menu, .comments, .sharing, .related"):
                            unwanted.decompose()
                        report_content = main_content
                
                if report_content:
                    # Clean up the content
                    for unwanted in report_content.select("script, style, iframe, noscript, .advertisement, .ad, .share-buttons"):
                        unwanted.decompose()
                    
                    # Get the HTML content
                    article_data["content"] = str(report_content)
                    
                    # Convert to markdown
                    article_data["markdown"] = self.clean_markdown(h2t.handle(article_data["content"]))
                    
                    # Look for paragraphs and headings for the summary
                    paragraphs = [p.get_text().strip() for p in report_content.select("p, h2, h3") if p.get_text().strip()]
                    if paragraphs:
                        summary = " ".join(paragraphs[:3])
                        article_data["summary"] = summary[:500] + "..." if len(summary) > 500 else summary
                        article_data["success"] = True
                    else:
                        # If we couldn't find paragraphs, use any text content
                        text_content = report_content.get_text().strip()
                        if text_content:
                            article_data["summary"] = text_content[:500] + "..." if len(text_content) > 500 else text_content
                            article_data["success"] = True
                    
                    # If we have a title and some content, consider it a success
                    if article_data["title"] and article_data["markdown"]:
                        article_data["success"] = True
                        logger.info("Successfully extracted report content")
                
                # Look for a thumbnail image
                thumbnail = soup.select_one("meta[property='og:image']") or soup.select_one(".single-post__featured-image img")
                if thumbnail:
                    img_url = thumbnail.get("content") if thumbnail.name == "meta" else thumbnail.get("src", "")
                    if img_url:
                        article_data["thumbnail"] = img_url
                        logger.info(f"Found report thumbnail: {img_url}")
                
                return article_data
            
            # Standard article content extraction for non-report articles
            content_elem = (
                soup.select_one(".post-content") or
                soup.select_one(".article-content") or
                soup.select_one(".entry-content") or
                soup.select_one(".single-post__content") or
                soup.select_one(".content") or
                soup.select_one(".article__body") or
                soup.select_one("article")
            )
            
            if content_elem:
                # Remove unwanted elements
                for unwanted in content_elem.select(".advertisement, .ad, .share-buttons, .related-posts, .author-box, .comments, .bm-partner-label, .faq-content"):
                    unwanted.decompose()
                
                # Get the HTML content
                article_data["content"] = str(content_elem)
                
                # Clean up the content - remove scripts, iframes, etc.
                for script in BeautifulSoup(article_data["content"], "html.parser").find_all(["script", "iframe", "style", "noscript"]):
                    script.decompose()
                
                # Convert to markdown
                article_data["markdown"] = self.clean_markdown(h2t.handle(article_data["content"]))
                
                # Create a summary (first 3 paragraphs or 500 chars)
                paragraphs = [p.get_text().strip() for p in content_elem.select("p") if p.get_text().strip()]
                
                if paragraphs:
                    # Use first 3 non-empty paragraphs for summary
                    summary = " ".join(paragraphs[:3])
                    article_data["summary"] = summary[:500] + "..." if len(summary) > 500 else summary
                    logger.info(f"Created article summary ({len(article_data['summary'])} chars)")
                    
                    # Article was successfully parsed
                    article_data["success"] = True
                else:
                    logger.warning(f"No paragraphs found in article content")
            else:
                logger.warning(f"Could not find article content element")
            
            # Additional processing for external content (like wallets page)
            if "ext/bestwallet" in url or "ext/" in url:
                # For external pages, use the page title as article title if not already set
                if not article_data["title"]:
                    title_tag = soup.find("title")
                    if title_tag:
                        article_data["title"] = title_tag.get_text().strip()
                        
                # Use the main content of the page
                main_content = soup.select_one("main") or soup.select_one(".main") or soup.select_one(".content")
                if main_content:
                    # Get the HTML content
                    article_data["content"] = str(main_content)
                    
                    # Convert to markdown
                    article_data["markdown"] = self.clean_markdown(h2t.handle(article_data["content"]))
                    
                    # Create summary from headings if no paragraphs
                    if not article_data["summary"]:
                        headings = [h.get_text().strip() for h in main_content.select("h1, h2, h3")]
                        if headings:
                            article_data["summary"] = " - ".join(headings[:3])
                    
                    article_data["success"] = True
            
            return article_data
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return article_data
    
    def clean_markdown(self, markdown_text: str) -> str:
        """
        Clean and format markdown text.
        
        Args:
            markdown_text: Raw markdown text
            
        Returns:
            Cleaned markdown text
        """
        # Remove multiple consecutive newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', markdown_text)
        
        # Remove empty links
        cleaned = re.sub(r'\[\]\(.*?\)', '', cleaned)
        
        # Fix formatting issues
        cleaned = re.sub(r'\*\*\s+', '** ', cleaned)
        cleaned = re.sub(r'\s+\*\*', ' **', cleaned)
        
        # Remove HTML artifacts
        cleaned = re.sub(r'</?[a-z][^>]*>', '', cleaned)
        
        return cleaned.strip()
    
    def create_safe_filename(self, title: str) -> str:
        """
        Create a safe filename from article title.
        
        Args:
            title: Article title
            
        Returns:
            Safe filename string
        """
        # Replace spaces with underscores and remove special characters
        safe_name = re.sub(r'[^\w\s-]', '', title.lower())
        safe_name = re.sub(r'[\s-]+', '_', safe_name)
        
        # Truncate if too long
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
            
        return safe_name
    
    def save_article(self, article_data: Dict[str, Any]) -> str:
        """
        Save article data to files.
        
        Args:
            article_data: Dictionary containing article data
            
        Returns:
            Path to the saved markdown file
        """
        if not article_data["success"]:
            logger.warning(f"Not saving unsuccessful article: {article_data['url']}")
            return ""
            
        try:
            # Create timestamp and safe filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_base = self.create_safe_filename(article_data["title"])
            
            # Create filenames
            md_filename = f"{timestamp}_{filename_base}.md"
            json_filename = f"{timestamp}_{filename_base}.json"
            
            # Save markdown file
            md_path = self.output_path / md_filename
            with open(md_path, "w", encoding="utf-8") as f:
                # Create markdown header
                header = f"# {article_data['title']}\n\n"
                if article_data["date"]:
                    header += f"**Date:** {article_data['date']}\n\n"
                if article_data["author"]:
                    header += f"**Author:** {article_data['author']}\n\n"
                if article_data["tags"]:
                    header += f"**Tags:** {', '.join(article_data['tags'])}\n\n"
                header += f"**URL:** {article_data['url']}\n\n"
                header += "---\n\n"
                
                # Combine header and content
                f.write(header + article_data["markdown"])
            
            # Save JSON file with all data
            json_path = self.output_path / json_filename
            with open(json_path, "w", encoding="utf-8") as f:
                # Add extraction timestamp to the data
                article_data["extraction_time"] = timestamp
                json.dump(article_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved article: {article_data['title']} to {md_path}")
            return str(md_path)
            
        except Exception as e:
            logger.error(f"Error saving article: {e}")
            return ""
    
    def crawl(self):
        """
        Main crawling method that processes sections and articles.
        """
        try:
            if not self.setup_driver():
                logger.error("Failed to set up the browser. Exiting.")
                return
                
            # Process each section
            sections_processed = 0
            for section in DEFAULT_SECTIONS[:self.max_sections]:
                section_url = urljoin(BASE_URL, section)
                logger.info(f"Processing section: {section_url}")
                
                # Extract article links from the section
                article_links = self.extract_article_links(section_url)
                
                # Process each article
                for article_url in article_links:
                    if self.results["articles_scraped"] >= self.max_articles * self.max_sections:
                        logger.info(f"Reached maximum number of articles ({self.max_articles * self.max_sections}). Stopping.")
                        break
                        
                    logger.info(f"Processing article: {article_url}")
                    
                    # Extract article content
                    article_data = self.extract_article_content(article_url)
                    self.results["articles_scraped"] += 1
                    
                    # Save the article if extraction was successful
                    if article_data["success"]:
                        saved_path = self.save_article(article_data)
                        if saved_path:
                            self.results["successful_scrapes"] += 1
                            self.results["articles"].append({
                                "url": article_url,
                                "title": article_data["title"],
                                "saved_path": saved_path
                            })
                    else:
                        self.results["failed_scrapes"] += 1
                        
                    # Wait between requests
                    self.wait_random(3, 7)
                
                sections_processed += 1
                self.results["sections_crawled"] = sections_processed
                
                # Save progress after each section
                self.save_crawl_results()
                
                if sections_processed >= self.max_sections:
                    logger.info(f"Reached maximum number of sections ({self.max_sections}). Stopping.")
                    break
                    
        except Exception as e:
            logger.error(f"Error in crawl process: {e}")
        finally:
            # Save final results
            self.save_crawl_results()
            
            # Close the browser
            self.close_driver()
    
    def save_crawl_results(self):
        """Save crawling results to a JSON file."""
        try:
            # Update end time
            self.results["end_time"] = datetime.now().isoformat()
            
            # Calculate duration
            start_time = datetime.fromisoformat(self.results["start_time"])
            end_time = datetime.fromisoformat(self.results["end_time"])
            duration_seconds = (end_time - start_time).total_seconds()
            self.results["duration_seconds"] = duration_seconds
            
            # Save results
            results_path = self.output_path / "crawl_results.json"
            with open(results_path, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved crawl results to {results_path}")
            
        except Exception as e:
            logger.error(f"Error saving crawl results: {e}")

def main():
    """Main function to parse arguments and run the crawler."""
    parser = argparse.ArgumentParser(description="CryptoNews.com Selenium Crawler")
    parser.add_argument("--output-dir", type=str, default="scraped_data",
                        help="Directory to save scraped data")
    parser.add_argument("--max-articles", type=int, default=5,
                        help="Maximum number of articles to scrape per section")
    parser.add_argument("--max-sections", type=int, default=3,
                        help="Maximum number of sections to scrape")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="Maximum number of retries for failed requests")
    parser.add_argument("--visible", action="store_true",
                        help="Run with visible browser instead of headless")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    logger.info(f"Starting CryptoNews.com crawler with configuration:")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Max articles: {args.max_articles}")
    logger.info(f"Max sections: {args.max_sections}")
    logger.info(f"Max retries: {args.max_retries}")
    logger.info(f"Headless mode: {not args.visible}")
    
    # Create and run the crawler
    crawler = CryptoNewsSeleniumCrawler(
        output_dir=args.output_dir,
        max_articles=args.max_articles,
        max_sections=args.max_sections,
        headless=not args.visible,
        max_retries=args.max_retries
    )
    
    crawler.crawl()
    
    logger.info("Crawling completed!")
    logger.info(f"Sections crawled: {crawler.results['sections_crawled']}")
    logger.info(f"Articles scraped: {crawler.results['articles_scraped']}")
    logger.info(f"Successful scrapes: {crawler.results['successful_scrapes']}")
    logger.info(f"Failed scrapes: {crawler.results['failed_scrapes']}")

if __name__ == "__main__":
    main() 