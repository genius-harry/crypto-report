#!/usr/bin/env python3
"""
Selenium-based Web Crawler

This module implements a web crawler that uses Selenium to handle
JavaScript-rendered websites like CoinDesk, where content might
be dynamically loaded.
"""

import os
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import html2text

# Try importing Selenium and WebDriver Manager (will need to be installed)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    
    # Try to use webdriver_manager if available
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.core.os_manager import ChromeType
        WEBDRIVER_MANAGER_AVAILABLE = True
    except ImportError:
        WEBDRIVER_MANAGER_AVAILABLE = False
    
    SELENIUM_AVAILABLE = True
except ImportError:
    print("Selenium not available. Install with: pip install selenium webdriver-manager")
    print("You will also need ChromeDriver if not using webdriver-manager: https://sites.google.com/chromium.org/driver/")
    SELENIUM_AVAILABLE = False
    WEBDRIVER_MANAGER_AVAILABLE = False

# Import functions from bs_crawler
from bs_crawler import (
    clean_markdown, create_markdown_filename,
    extract_title, extract_author, extract_date, extract_description,
    extract_featured_image, html_to_markdown
)

def setup_selenium_driver():
    """
    Set up and return a Selenium WebDriver for Chrome.
    
    Returns:
        WebDriver instance or None if Selenium is not available
    """
    if not SELENIUM_AVAILABLE:
        return None
        
    try:
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode (no UI)
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-notifications")
        
        # Initialize the WebDriver using webdriver_manager if available
        if WEBDRIVER_MANAGER_AVAILABLE:
            try:
                # For macOS, we'll try to use ChromeDriverManager with the Chrome type
                if os.name == 'posix' and 'darwin' in os.sys.platform:
                    service = Service(ChromeDriverManager().install())
                else:
                    service = Service(ChromeDriverManager().install())
                
                driver = webdriver.Chrome(service=service, options=chrome_options)
                return driver
            except Exception as e:
                print(f"Error setting up with webdriver_manager: {e}")
                # Fall back to default
                pass
        
        # If webdriver_manager is not available or fails, try default Chrome setup
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except WebDriverException as e:
        print(f"Error setting up Selenium: {e}")
        print("If using macOS, try: pip install webdriver-manager")
        print("Then reinstall with: pip install selenium")
        return None

def scrape_with_selenium(url: str, wait_time: int = 5) -> Optional[Dict[str, Any]]:
    """
    Scrape a URL using Selenium to handle JavaScript-rendered content.
    
    Args:
        url: The URL to scrape
        wait_time: How long to wait for the page to load (in seconds)
        
    Returns:
        Dictionary with scraped content or None if scraping failed
    """
    driver = setup_selenium_driver()
    if not driver:
        print("Selenium WebDriver could not be initialized.")
        return None
    
    try:
        print(f"Loading {url} with Selenium...")
        driver.get(url)
        
        # Wait for the content to load
        time.sleep(wait_time)
        
        # Check if it's a CoinDesk article and wait for specific elements
        if "coindesk.com" in url:
            try:
                # Wait for article content to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "article"))
                )
            except TimeoutException:
                print("Timeout waiting for article content to load")
        
        # Get the page source after JavaScript has rendered
        html_content = driver.page_source
        
        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract metadata and content
        result = extract_article_data_selenium(soup, url)
        
        # Add scraping metadata
        result["metadata"]["url"] = url
        result["metadata"]["scraped_at"] = datetime.now().isoformat()
        result["metadata"]["selenium"] = True
        result["html"] = html_content  # Store original HTML
        
        return result
        
    except Exception as e:
        print(f"Error scraping {url} with Selenium: {e}")
        return None
    finally:
        # Always close the driver to free resources
        if driver:
            driver.quit()

def extract_article_data_selenium(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    """
    Extract article data from BeautifulSoup object generated by Selenium.
    
    Args:
        soup: BeautifulSoup object from Selenium-rendered page
        url: The URL of the article
        
    Returns:
        Dictionary with extracted article data
    """
    result = {
        "metadata": {},
        "content": "",
        "markdown": "",
    }
    
    # Extract title
    result["metadata"]["title"] = extract_title(soup)
    
    # Extract date
    result["metadata"]["date"] = extract_date(soup)
    
    # Extract author
    result["metadata"]["author"] = extract_author(soup)
    
    # Extract description/summary
    result["metadata"]["description"] = extract_description(soup)
    
    # Extract featured image
    result["metadata"]["image"] = extract_featured_image(soup, url)
    
    # Extract source domain
    result["metadata"]["source"] = urlparse(url).netloc.replace("www.", "")
    
    # Extract main content with site-specific handling
    if "coindesk.com" in url:
        main_content_html = extract_coindesk_content(soup)
    else:
        main_content_html = extract_generic_content(soup)
    
    if main_content_html:
        # Clean up the content
        result["content"] = main_content_html.get_text(" ", strip=True)
        
        # Convert to markdown
        result["markdown"] = html_to_markdown(str(main_content_html))
    
    return result

def extract_coindesk_content(soup: BeautifulSoup) -> Optional[BeautifulSoup]:
    """
    Extract the main content from a CoinDesk article.
    
    Args:
        soup: BeautifulSoup object of the page
        
    Returns:
        BeautifulSoup object containing the main content or None
    """
    # Try to find the article content by CoinDesk's structure
    content = None
    
    # Method 1: Look for the main article section
    article = soup.find("article")
    if article:
        # Find the main content within the article
        content_section = article.find("div", class_=lambda c: c and ("content" in c.lower() or "story" in c.lower()))
        if content_section:
            content = content_section
    
    # Method 2: If not found, try another common pattern
    if not content:
        content = soup.find("div", class_=lambda c: c and ("at-content" in c.lower()))
    
    # Method 3: Look for content based on structure
    if not content:
        # Find sections with multiple paragraphs
        sections = []
        for section in soup.find_all(["div", "section"]):
            paragraphs = section.find_all("p")
            if len(paragraphs) > 3:  # Articles typically have multiple paragraphs
                sections.append((section, len(paragraphs)))
        
        if sections:
            # Sort by number of paragraphs (most first)
            sections.sort(key=lambda x: x[1], reverse=True)
            content = sections[0][0]
    
    if content:
        # Clean up the content
        for unwanted in content.find_all(["script", "style", "nav", "aside", "form", 
                                         "div"], class_=re.compile(r"ad|promo|newsletter|signup|social", re.I)):
            unwanted.decompose()
            
        return content
    
    return None

def extract_generic_content(soup: BeautifulSoup) -> Optional[BeautifulSoup]:
    """
    Extract the main content from a generic article.
    
    Args:
        soup: BeautifulSoup object of the page
        
    Returns:
        BeautifulSoup object containing the main content or None
    """
    # Try standard article containers
    containers = [
        soup.find("article"),
        soup.find("main"),
        soup.find(["div", "section"], class_=re.compile(r"article|post|content|main", re.I)),
        soup.find(id=re.compile(r"article|post|content|main", re.I)),
    ]
    
    content = next((c for c in containers if c is not None), None)
    
    if not content:
        # Find the div with the most paragraph tags
        p_counts = {}
        for div in soup.find_all("div"):
            paragraphs = div.find_all("p")
            if len(paragraphs) > 2:  # At least 3 paragraphs
                p_counts[div] = len(paragraphs)
        
        if p_counts:
            content = max(p_counts.items(), key=lambda x: x[1])[0]
    
    if content:
        # Clean up the content
        for unwanted in content.find_all(["script", "style", "nav", "header", "footer", 
                                         "aside", "form", "iframe"]):
            unwanted.decompose()
        
        return content
    
    return None

def save_selenium_article(url: str, output_path: str = None) -> str:
    """
    Scrape an article with Selenium and save it as markdown.
    
    Args:
        url: The URL to scrape
        output_path: Path to save the article (if None, will create one)
        
    Returns:
        Path to the saved file or empty string if failed
    """
    # Scrape the article
    result = scrape_with_selenium(url)
    
    if not result:
        print(f"Failed to scrape {url} with Selenium")
        return ""
    
    # Create output directory if it doesn't exist
    if not output_path:
        os.makedirs("scraped_articles", exist_ok=True)
        title = result["metadata"].get("title", "")
        filename = create_markdown_filename(url, title)
        output_path = os.path.join("scraped_articles", filename)
    
    # Save the markdown content
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# {result['metadata'].get('title', 'Untitled Article')}\n\n")
        f.write(f"Source: {url}\n")
        
        # Add metadata
        for key, value in result["metadata"].items():
            if key not in ["title", "url", "selenium"] and value:
                f.write(f"{key.capitalize()}: {value}\n")
        
        f.write("\n")
        f.write(result.get("markdown", ""))
    
    print(f"Saved article to {output_path}")
    return output_path

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape a website using Selenium")
    parser.add_argument("url", help="URL of the article to scrape")
    parser.add_argument("--output", help="Output file path (optional)")
    
    args = parser.parse_args()
    
    # Check if Selenium is available
    if not SELENIUM_AVAILABLE:
        print("Error: Selenium is not available.")
        print("Please install selenium: pip install selenium")
        print("And download ChromeDriver: https://sites.google.com/chromium.org/driver/")
        return
    
    # Scrape and save the article
    output_path = save_selenium_article(args.url, args.output)
    
    if output_path:
        print(f"Successfully scraped and saved to {output_path}")
    else:
        print(f"Failed to scrape {args.url}")

if __name__ == "__main__":
    main() 