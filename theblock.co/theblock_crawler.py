#!/usr/bin/env python3
"""
The Block Crypto News Crawler with Selenium

This script crawls The Block (theblock.co) website to fetch cryptocurrency news articles
using Selenium to render JavaScript and bypass Cloudflare protection.
Saves articles in markdown and JSON formats.
"""

import os
import sys
import json
import time
import random
import re
import argparse
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

# Base URL and categories
BASE_URL = "https://www.theblock.co"
CATEGORIES = {
    "latest": "/latest",
    "bitcoin": "/category/bitcoin",
    "ethereum": "/category/ethereum",
    "defi": "/category/defi",
    "business": "/category/business",
    "policy": "/category/policy-regulation",
}

class TheBlockCrawler:
    """Crawler for The Block (theblock.co) news articles using Selenium."""
    
    def __init__(self, output_dir="scraped_data", max_articles=10, category="latest", headless=True):
        """
        Initialize the crawler.
        
        Args:
            output_dir (str): Directory to save the scraped data
            max_articles (int): Maximum number of articles to fetch
            category (str): Category of articles to fetch
            headless (bool): Whether to run the browser in headless mode
        """
        self.output_dir = output_dir
        self.max_articles = max_articles
        self.category = category
        self.headless = headless
        self.driver = self._setup_selenium_driver()
        
        # Create a timestamped directory for this crawl
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(output_dir, timestamp)
        os.makedirs(self.output_dir, exist_ok=True)
        
        print(f"Output directory: {self.output_dir}")
    
    def _setup_selenium_driver(self):
        """Set up and return a Selenium WebDriver."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")  # Updated headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Add user agent to avoid detection - using a more modern User-Agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
        
        # Disable webdriver detection
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Add preferences to better handle Cloudflare
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "download.default_directory": "/dev/null",
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            
            # Additional bypass for detection
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // Overwrite the 'plugins' property to use a custom getter
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    
                    // Overwrite the 'languages' property to use a custom getter
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en', 'es']
                    });
                    
                    // Overwrite the 'platform' property to use a custom getter
                    Object.defineProperty(navigator, 'platform', {
                        get: () => 'MacIntel'
                    });
                """
            })
            
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
    
    def get_article_links(self, category_url):
        """
        Get article links from a category page.
        
        Args:
            category_url (str): URL of the category page
            
        Returns:
            list: List of article URLs
        """
        links = []
        
        try:
            print(f"Loading category page: {category_url}")
            self.driver.get(category_url)
            
            # Increase wait time for Cloudflare challenge to complete
            print("Waiting for page to load, including potential Cloudflare challenges...")
            time.sleep(10)  # Give more time for Cloudflare challenge
            
            # Try to wait for either article elements or specific class names
            try:
                # Try multiple selectors that might indicate page is loaded
                selectors = [
                    (By.TAG_NAME, "article"),
                    (By.CSS_SELECTOR, ".article-card"),
                    (By.CSS_SELECTOR, ".post"),
                    (By.CSS_SELECTOR, ".news-item"),
                    (By.CSS_SELECTOR, ".entry"),
                    (By.CSS_SELECTOR, "h1")
                ]
                
                for selector_type, selector in selectors:
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((selector_type, selector))
                        )
                        print(f"Page loaded - found elements matching: {selector}")
                        break
                    except TimeoutException:
                        continue
            except Exception as e:
                print(f"Warning: Timed out waiting for specific elements, continuing anyway: {e}")
            
            # Print page title for debugging
            print(f"Page title: {self.driver.title}")
            
            # Give extra time for all content to load
            self._wait(3, 5)
            
            # If we get a Cloudflare challenge or Access Denied, print this
            if "Cloudflare" in self.driver.title or "Attention Required" in self.driver.title:
                print("Detected Cloudflare challenge page. Waiting longer...")
                time.sleep(15)  # Wait even longer for manual challenge
                
            # Parse the page source
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Save the HTML for debugging
            debug_path = os.path.join(self.output_dir, "debug_page.html")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print(f"Saved page HTML to {debug_path} for debugging")
            
            # Try different approaches to find article links
            
            # Approach 1: Find article tags
            articles = soup.find_all('article')
            
            # Approach 2: Find div elements with specific classes
            if not articles:
                print("No <article> tags found, trying alternative selectors...")
                articles = soup.find_all(['div', 'a'], class_=lambda c: c and any(x in c for x in ['article', 'post', 'entry', 'news-item']))
            
            # Approach 3: Find heading elements with links
            if not articles:
                print("Trying to find headings with links...")
                headings = soup.find_all(['h1', 'h2', 'h3'], class_=lambda c: c and any(x in c for x in ['title', 'heading']))
                for heading in headings:
                    link_element = heading.find('a', href=True)
                    if link_element and link_element['href']:
                        link = link_element['href']
                        # Make sure the link is absolute
                        if link.startswith('/'):
                            link = BASE_URL + link
                        links.append(link)
            
            # Process found articles
            for article in articles:
                link_element = article.find('a', href=True)
                if link_element and link_element['href']:
                    link = link_element['href']
                    # Make sure the link is absolute
                    if link.startswith('/'):
                        link = BASE_URL + link
                    links.append(link)
            
            # If still no links, try a more generic approach - find any link that could be an article
            if not links:
                print("No article links found with standard methods, trying generic approach...")
                all_links = soup.find_all('a', href=True)
                for link_element in all_links:
                    href = link_element.get('href', '')
                    # Filter for paths that look like article URLs (usually contain year or article-like paths)
                    if href and ('20' in href or 'article' in href or 'news' in href or 'story' in href):
                        link = href
                        # Make sure the link is absolute
                        if link.startswith('/'):
                            link = BASE_URL + link
                        links.append(link)
            
            # Remove duplicates
            links = list(dict.fromkeys(links))
            
            print(f"Found {len(links)} article links")
            
        except TimeoutException:
            print("Timeout waiting for category page to load")
        except Exception as e:
            print(f"Error getting article links: {e}")
        
        return links[:self.max_articles]
    
    def fetch_article_content(self, url):
        """
        Fetch article content using Selenium.
        
        Args:
            url (str): URL of the article
            
        Returns:
            tuple: (article_data, success_flag)
        """
        try:
            print(f"Loading article: {url}")
            self.driver.get(url)
            
            # Wait for title to be present
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1, .article-title, .post-title"))
            )
            
            # Give extra time for content to load
            self._wait(3, 5)
            
            # Get page title
            title = ""
            try:
                title_element = self.driver.find_element(By.CSS_SELECTOR, "h1, .article-title, .post-title")
                title = title_element.text
                print(f"Article title: {title}")
            except Exception as e:
                print(f"Error extracting title: {e}")
            
            # Get article content
            content_html = ""
            
            # Try different selectors for the article content
            selectors = [
                ".article-content", ".post-content", ".entry-content", "article .content", 
                "main article", ".article__body", ".article-body"
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        content_html = elements[0].get_attribute('outerHTML')
                        print(f"Found article content using selector: {selector}")
                        break
                except Exception:
                    continue
            
            # Get publication date
            date_str = ""
            date_selectors = [
                "time", ".date", ".published", ".post-date", ".article-date", 
                ".entry-date", "meta[property='article:published_time']"
            ]
            
            for selector in date_selectors:
                try:
                    date_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if date_elements:
                        if 'meta' in selector:
                            date_str = date_elements[0].get_attribute('content')
                        else:
                            date_str = date_elements[0].text
                            
                        # Try to parse and format the date
                        try:
                            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            date_str = date_obj.isoformat()
                        except ValueError:
                            pass
                            
                        break
                except Exception:
                    continue
            
            # Get author information
            author = ""
            author_selectors = [
                ".author-name", ".byline", ".author", "meta[name='author']", 
                "meta[property='article:author']", ".article-author", ".post-author"
            ]
            
            for selector in author_selectors:
                try:
                    author_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if author_elements:
                        if 'meta' in selector:
                            author = author_elements[0].get_attribute('content')
                        else:
                            author = author_elements[0].text
                        break
                except Exception:
                    continue
            
            # Get categories/tags
            categories = []
            try:
                category_elements = self.driver.find_elements(By.CSS_SELECTOR, ".category a, .categories a, .tags a, .post-categories a")
                for elem in category_elements:
                    cat_text = elem.text.strip()
                    if cat_text:
                        categories.append(cat_text)
            except Exception:
                pass
            
            # Convert HTML content to markdown
            content_markdown = h2t.handle(content_html) if content_html else ""
            
            # Clean up the markdown content
            content_markdown = self._clean_markdown(content_markdown)
            
            # Create article data
            article_data = {
                'title': title,
                'url': url,
                'publication_date': date_str,
                'author': author,
                'content': content_markdown,
                'html_content': content_html,
                'categories': categories,
                'source': 'The Block'
            }
            
            return article_data, True
            
        except TimeoutException:
            print(f"Timeout loading article: {url}")
            return None, False
        except Exception as e:
            print(f"Error fetching article content: {e}")
            return None, False
    
    def _clean_markdown(self, markdown_text):
        """
        Clean up markdown text by removing extra spaces, fixing linebreaks, etc.
        
        Args:
            markdown_text (str): Original markdown text
            
        Returns:
            str: Cleaned markdown text
        """
        if not markdown_text:
            return ""
        
        # Remove consecutive blank lines
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
        
        # Remove extra spaces at the beginning of lines
        markdown_text = re.sub(r'^\s+', '', markdown_text, flags=re.MULTILINE)
        
        # Fix markdown links with extra spaces
        markdown_text = re.sub(r'\[ ([^\]]+) \]', r'[\1]', markdown_text)
        
        return markdown_text.strip()
    
    def create_safe_filename(self, title):
        """
        Create a safe filename from the article title.
        
        Args:
            title (str): Article title
            
        Returns:
            str: Safe filename
        """
        # Replace invalid characters with underscore
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", title)
        
        # Replace multiple spaces/underscores with a single underscore
        safe_name = re.sub(r'[\s_]+', "_", safe_name)
        
        # Limit length and convert to lowercase
        safe_name = safe_name.lower()[:100]
        
        # Remove leading/trailing underscores
        safe_name = safe_name.strip("_")
        
        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"{timestamp}_{safe_name}"
    
    def save_article(self, article_data):
        """
        Save article data to files (markdown and JSON).
        
        Args:
            article_data (dict): Article data
            
        Returns:
            tuple: (markdown_path, json_path)
        """
        filename = self.create_safe_filename(article_data['title'])
        
        # Create directories if they don't exist
        markdown_dir = os.path.join(self.output_dir, 'markdown')
        json_dir = os.path.join(self.output_dir, 'json')
        
        os.makedirs(markdown_dir, exist_ok=True)
        os.makedirs(json_dir, exist_ok=True)
        
        # Paths for markdown and JSON files
        markdown_path = os.path.join(markdown_dir, f"{filename}.md")
        json_path = os.path.join(json_dir, f"{filename}.json")
        
        # Create markdown content
        markdown_content = f"# {article_data['title']}\n\n"
        
        if article_data['publication_date']:
            markdown_content += f"Date: {article_data['publication_date']}\n\n"
            
        if article_data['author']:
            markdown_content += f"Author: {article_data['author']}\n\n"
            
        if article_data['categories']:
            markdown_content += f"Categories: {', '.join(article_data['categories'])}\n\n"
            
        markdown_content += f"Source: [The Block]({article_data['url']})\n\n"
        markdown_content += "---\n\n"
        markdown_content += article_data['content']
        
        # Save markdown file
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        # Save JSON file (exclude html_content to save space)
        json_data = {k: v for k, v in article_data.items() if k != 'html_content'}
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
            
        return markdown_path, json_path
    
    def process_articles(self):
        """
        Process articles from the specified category.
        
        Returns:
            list: List of processed article data
        """
        processed_articles = []
        
        try:
            # Get category URL
            if self.category in CATEGORIES:
                category_url = BASE_URL + CATEGORIES[self.category]
            else:
                print(f"Invalid category: {self.category}. Using 'latest' instead.")
                category_url = BASE_URL + CATEGORIES["latest"]
                
            print(f"Processing category: {self.category} at {category_url}")
            
            # Get article links
            article_links = self.get_article_links(category_url)
            
            if not article_links:
                print("No article links found.")
                return []
                
            print(f"Processing {len(article_links)} articles...")
            
            # Process each article
            for i, url in enumerate(article_links):
                try:
                    print(f"\nProcessing article {i+1}/{len(article_links)}: {url}")
                    
                    # Fetch article content
                    article_data, success = self.fetch_article_content(url)
                    
                    if not success or not article_data:
                        print(f"Failed to fetch article: {url}")
                        continue
                        
                    # Save article
                    markdown_path, json_path = self.save_article(article_data)
                    
                    print(f"Saved article: {os.path.basename(markdown_path)}")
                    processed_articles.append(article_data)
                    
                    # Wait to avoid overloading the server
                    if i < len(article_links) - 1:
                        self._wait(2, 5)
                        
                except Exception as e:
                    print(f"Error processing article {url}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error in process_articles: {e}")
            
        return processed_articles
    
    def run(self):
        """
        Run the crawler.
        
        Returns:
            int: Number of articles processed
        """
        print(f"Starting The Block crawler for category: {self.category}")
        print(f"Max articles: {self.max_articles}")
        
        try:
            processed_articles = self.process_articles()
            
            num_articles = len(processed_articles)
            print(f"\nCrawling completed. Processed {num_articles} articles.")
            
            # Generate a summary
            summary = {
                'timestamp': datetime.now().isoformat(),
                'category': self.category,
                'num_articles': num_articles,
                'output_dir': self.output_dir,
                'articles': [
                    {
                        'title': article['title'],
                        'url': article['url'],
                        'date': article['publication_date'],
                        'author': article['author']
                    }
                    for article in processed_articles
                ]
            }
            
            # Save summary
            summary_path = os.path.join(self.output_dir, 'summary.json')
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
                
            print(f"Summary saved to: {summary_path}")
            
            return num_articles
            
        except Exception as e:
            print(f"Error in run: {e}")
            return 0
        finally:
            # Clean up
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass


def main():
    """Main function to run the crawler."""
    parser = argparse.ArgumentParser(description='The Block Crypto News Crawler with Selenium')
    parser.add_argument('-a', '--articles', type=int, default=10, help='Maximum number of articles to fetch')
    parser.add_argument('-c', '--category', type=str, default='latest', choices=list(CATEGORIES.keys()), help='Category to crawl')
    parser.add_argument('-o', '--output', type=str, default='scraped_data', help='Output directory')
    parser.add_argument('--no-headless', action='store_true', help='Run browser in non-headless mode (visible)')
    
    args = parser.parse_args()
    
    headless = not args.no_headless
    
    crawler = TheBlockCrawler(
        output_dir=args.output,
        max_articles=args.articles,
        category=args.category,
        headless=headless
    )
    
    crawler.run()


if __name__ == "__main__":
    main() 