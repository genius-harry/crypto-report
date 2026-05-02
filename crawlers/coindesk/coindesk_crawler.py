#!/usr/bin/env python3
"""
CoinDesk Custom Crawler

A specialized crawler for CoinDesk.com that handles JavaScript rendering
and extracts content from all relevant sections of the site.
"""

import os
import sys
import json
import time
import re
import argparse
import random
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
import html2text

# Try importing Selenium (will need to be installed)
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

# CoinDesk-specific configurations
COINDESK_CONFIG = {
    "base_url": "https://www.coindesk.com",
    "sections": [
        "/markets",
        "/business",
        "/tech",
        "/policy",
        "/finance",
        "/consensus",
        "/opinion"
    ],
    "article_patterns": [
        # Date-based patterns
        r"/markets/20\d{2}/\d{2}/\d{2}/",
        r"/business/20\d{2}/\d{2}/\d{2}/",
        r"/tech/20\d{2}/\d{2}/\d{2}/",
        r"/policy/20\d{2}/\d{2}/\d{2}/",
        r"/finance/20\d{2}/\d{2}/\d{2}/",
        r"/consensus/20\d{2}/\d{2}/\d{2}/",
        r"/opinion/20\d{2}/\d{2}/\d{2}/",
        
        # Generic article patterns without dates
        r"/markets/[^/]+$",
        r"/business/[^/]+$",
        r"/tech/[^/]+$",
        r"/policy/[^/]+$",
        r"/finance/[^/]+$",
        r"/consensus/[^/]+$",
        r"/opinion/[^/]+$"
    ],
    "excluded_patterns": [
        "/tag/",
        "/author/",
        "/about",
        "/newsletters",
        "/privacy",
        "/terms",
        "/price/",
        "/api/",
        "/podcasts"
    ],
    "headers": {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    },
    "delay_range": (1, 3)  # Random delay between requests in seconds (min, max)
}

# Implement utility functions directly instead of importing them

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

def extract_title(soup: BeautifulSoup) -> str:
    """Extract title from BeautifulSoup object."""
    # Try to find title in meta tags first
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"]
    
    # Try Twitter card
    twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
    if twitter_title and twitter_title.get("content"):
        return twitter_title["content"]
    
    # Try the page title
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        return title_tag.string.strip()
    
    # Try article heading
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    
    return "Untitled Article"

def extract_author(soup: BeautifulSoup) -> str:
    """Extract author from BeautifulSoup object."""
    # Try meta tags first
    author_meta = soup.find("meta", property="article:author") or soup.find("meta", attrs={"name": "author"})
    if author_meta and author_meta.get("content"):
        return author_meta["content"]
    
    # Try schema.org markup
    author_element = soup.find(attrs={"itemprop": "author"})
    if author_element:
        name_element = author_element.find(attrs={"itemprop": "name"})
        if name_element:
            return name_element.get_text(strip=True)
        return author_element.get_text(strip=True)
    
    # Try common author patterns
    byline = soup.find(class_=re.compile(r"byline|author|writer", re.I))
    if byline:
        return byline.get_text(strip=True)
    
    # Try looking for "By" or "Author:" in text
    by_pattern = re.compile(r"^\s*(?:By|Author:)\s+(.*?)$", re.I)
    for element in soup.find_all(["p", "div", "span"]):
        match = by_pattern.search(element.get_text())
        if match:
            return match.group(1)
    
    return ""

def extract_date(soup: BeautifulSoup) -> str:
    """Extract date from BeautifulSoup object."""
    # First, look specifically for time elements with datetime attribute
    time_tags = soup.find_all("time")
    for time_tag in time_tags:
        if time_tag.get("datetime") and not time_tag.get_text().strip().startswith("0 seconds"):
            return time_tag["datetime"]
    
    # Try article:published_time meta tag (most reliable for article dates)
    date_meta = (
        soup.find("meta", property="article:published_time") or
        soup.find("meta", property="og:published_time") or
        soup.find("meta", attrs={"name": "date"})
    )
    if date_meta and date_meta.get("content"):
        return date_meta["content"]
    
    # Try schema.org markup
    date_element = soup.find(attrs={"itemprop": "datePublished"})
    if date_element and date_element.get("content"):
        return date_element["content"]
    elif date_element:
        return date_element.get_text(strip=True)
    
    # Try common date patterns in divs/spans (avoid video player elements)
    date_containers = soup.find_all(class_=re.compile(r"date|time|publish", re.I))
    for container in date_containers:
        # Skip containers that are part of video players
        if container.find_parent(class_=re.compile(r"video|player", re.I)):
            continue
        
        # Skip containers with video-like text
        text = container.get_text(strip=True)
        if "seconds of" in text or "Volume" in text:
            continue
            
        return text
    
    # Fall back to a more generic search (but still avoid video timestamps)
    if time_tags:
        for time_tag in time_tags:
            text = time_tag.get_text(strip=True)
            if not any(x in text.lower() for x in ["seconds of", "volume", "0 seconds"]):
                return text
    
    return ""

def extract_description(soup: BeautifulSoup) -> str:
    """Extract description from BeautifulSoup object."""
    # Try meta tags first
    description_meta = (
        soup.find("meta", property="og:description") or
        soup.find("meta", attrs={"name": "description"}) or
        soup.find("meta", attrs={"name": "twitter:description"})
    )
    if description_meta and description_meta.get("content"):
        return description_meta["content"]
    
    # Try schema.org markup
    description_element = soup.find(attrs={"itemprop": "description"})
    if description_element:
        return description_element.get_text(strip=True)
    
    # Try first paragraph
    first_p = soup.find("p")
    if first_p:
        return first_p.get_text(strip=True)
    
    return ""

def extract_featured_image(soup: BeautifulSoup, base_url: str) -> str:
    """Extract featured image from BeautifulSoup object."""
    # Try meta tags first
    image_meta = (
        soup.find("meta", property="og:image") or
        soup.find("meta", attrs={"name": "twitter:image"})
    )
    if image_meta and image_meta.get("content"):
        # Make sure it's an absolute URL
        return urljoin(base_url, image_meta["content"])
    
    # Try schema.org markup
    image_element = soup.find(attrs={"itemprop": "image"})
    if image_element and image_element.get("src"):
        return urljoin(base_url, image_element["src"])
    elif image_element and image_element.get("content"):
        return urljoin(base_url, image_element["content"])
    
    # Try the first image in the article
    article = soup.find("article") or soup
    first_img = article.find("img")
    if first_img and first_img.get("src"):
        return urljoin(base_url, first_img["src"])
    
    return ""

def html_to_markdown(html_content: str) -> str:
    """Convert HTML to markdown using html2text."""
    h2t = html2text.HTML2Text()
    h2t.ignore_links = False
    h2t.ignore_images = False
    h2t.ignore_emphasis = False
    h2t.ignore_tables = False
    h2t.body_width = 0  # No wrapping
    
    # Remove script and style elements
    soup = BeautifulSoup(html_content, "html.parser")
    for element in soup(["script", "style"]):
        element.decompose()
    
    return h2t.handle(str(soup))

def clean_markdown(markdown_content: str) -> str:
    """Clean up markdown content by removing excessive whitespace, etc."""
    # Remove multiple blank lines
    markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
    
    # Remove spaces at the end of lines
    markdown_content = re.sub(r' +\n', '\n', markdown_content)
    
    # Fix markdown headers with no space after #
    markdown_content = re.sub(r'(#+)([^ #\n])', r'\1 \2', markdown_content)
    
    return markdown_content.strip()

def create_markdown_filename(url: str, title: str) -> str:
    """Create a clean filename for the article based on the title."""
    # Use current date as prefix
    date_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # If no title, try to get one from the URL
    if not title:
        parsed_url = urlparse(url)
        title = os.path.basename(parsed_url.path)
    
    # Clean up the title for use as a filename
    clean_title = re.sub(r'[^\w\s-]', '', title.lower())
    clean_title = re.sub(r'[-\s]+', '_', clean_title).strip('-_')
    
    # Truncate if too long
    if len(clean_title) > 50:
        clean_title = clean_title[:50]
    
    return f"{date_prefix}_{clean_title}.md"

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

def check_selenium_availability():
    """Check if Selenium is available and properly configured."""
    if not SELENIUM_AVAILABLE:
        print("Selenium is not available. Please install it with:")
        print("pip install selenium webdriver-manager")
        return False
        
    driver = setup_selenium_driver()
    if not driver:
        print("Failed to initialize Selenium WebDriver.")
        return False
        
    driver.quit()
    return True

def make_request(url: str, use_selenium: bool = True) -> Optional[Tuple[str, requests.Response]]:
    """
    Make an HTTP request with proper error handling.
    
    Args:
        url: URL to request
        use_selenium: Whether to use Selenium for JavaScript rendering
        
    Returns:
        Tuple of (HTML content, Response object) or None if request failed
    """
    # Apply rate limiting
    time.sleep(random.uniform(COINDESK_CONFIG["delay_range"][0], COINDESK_CONFIG["delay_range"][1]))
    
    if use_selenium and SELENIUM_AVAILABLE:
        driver = setup_selenium_driver()
        if driver:
            try:
                print(f"Loading {url} with Selenium...")
                driver.get(url)
                time.sleep(5)  # Wait for JavaScript to render content
                
                # Get the page source after JavaScript has rendered
                html_content = driver.page_source
                
                # Create a dummy response object
                class DummyResponse:
                    def __init__(self, url, html):
                        self.status_code = 200
                        self.url = url
                        self.text = html
                
                response = DummyResponse(url, html_content)
                return html_content, response
                
            except Exception as e:
                print(f"Selenium error for {url}: {e}")
            finally:
                driver.quit()
    
    # Fallback to regular requests or if Selenium is not specified
    try:
        print(f"Loading {url} with requests...")
        response = requests.get(url, headers=COINDESK_CONFIG["headers"], timeout=10)
        response.raise_for_status()
        return response.text, response
    except requests.RequestException as e:
        print(f"Error requesting {url}: {e}")
        return None

def get_page_links(url: str, visited_urls: Set[str] = None) -> List[Tuple[str, str]]:
    """
    Extract links from a CoinDesk page.
    
    Args:
        url: URL to extract links from
        visited_urls: Set of already visited URLs to avoid duplicates
        
    Returns:
        List of tuples (url, link_type) where link_type is 'article' or 'section'
    """
    if visited_urls is None:
        visited_urls = set()
    
    result = make_request(url, use_selenium=False)
    if not result:
        return []
        
    html_content, _ = result
    soup = BeautifulSoup(html_content, "html.parser")
    
    links = []
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    # Debug: Count various link types
    article_count = 0
    section_count = 0
    unknown_count = 0
    excluded_count = 0
    
    for link in soup.find_all("a", href=True):
        href = link["href"]
        
        # Skip empty links and anchors
        if not href or href.startswith("#"):
            continue
            
        # Make relative URLs absolute
        if href.startswith("/"):
            full_url = urljoin(base_url, href)
        elif href.startswith("http"):
            # Skip external links
            if not href.startswith(COINDESK_CONFIG["base_url"]):
                continue
            full_url = href
        else:
            continue
            
        # Skip if already visited
        if full_url in visited_urls:
            continue
            
        # Skip excluded patterns
        if any(pattern in full_url for pattern in COINDESK_CONFIG["excluded_patterns"]):
            excluded_count += 1
            continue
            
        # Determine if it's an article or a section
        link_type = "unknown"
        if any(re.search(pattern, full_url) for pattern in COINDESK_CONFIG["article_patterns"]):
            link_type = "article"
            article_count += 1
        elif any(section in full_url for section in COINDESK_CONFIG["sections"]):
            link_type = "section"
            section_count += 1
        else:
            unknown_count += 1
            
        if link_type != "unknown":
            links.append((full_url, link_type))
            visited_urls.add(full_url)
    
    # Debug: Print link counts
    print(f"Found: {article_count} articles, {section_count} sections, {unknown_count} unknown, {excluded_count} excluded")
    
    # Print a few example article links if any
    article_links = [url for url, link_type in links if link_type == "article"]
    if article_links:
        print("Example article links:")
        for i, url in enumerate(article_links[:3]):
            print(f"  {i+1}. {url}")
    
    return links

def scrape_article(url: str, output_dir: str) -> Dict[str, Any]:
    """
    Scrape a CoinDesk article using Selenium for JavaScript rendering.
    
    Args:
        url: URL of the article
        output_dir: Directory to save the article
        
    Returns:
        Dictionary with scraping results
    """
    print(f"Scraping article: {url}")
    
    # Use Selenium for article content
    result = make_request(url, use_selenium=True)
    if not result:
        return {"success": False, "url": url, "error": "Failed to load the article"}
        
    html_content, _ = result
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Extract metadata
    title = extract_title(soup)
    date = extract_date(soup)
    author = extract_author(soup)
    description = extract_description(soup)
    image = extract_featured_image(soup, url)
    
    # Extract main content
    main_content = extract_coindesk_content(soup)
    
    if not main_content:
        # Try alternative extraction methods
        article = soup.find("article")
        if article:
            main_content = article
    
    if not main_content:
        return {"success": False, "url": url, "error": "Could not extract article content"}
        
    # Convert to markdown
    markdown_content = html_to_markdown(str(main_content))
    markdown_content = clean_markdown(markdown_content)
    
    # Prepare result data
    result = {
        "metadata": {
            "title": title,
            "date": date,
            "author": author,
            "description": description,
            "image": image,
            "url": url,
            "source": "coindesk.com",
            "scraped_at": datetime.now().isoformat()
        },
        "markdown": markdown_content
    }
    
    # Create output filename
    filename = create_markdown_filename(url, title)
    output_path = os.path.join(output_dir, filename)
    
    # Save as markdown
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"Source: {url}\n")
        
        # Add metadata
        for key, value in result["metadata"].items():
            if key not in ["title", "url"] and value:
                f.write(f"{key.capitalize()}: {value}\n")
                
        f.write("\n")
        f.write(markdown_content)
    
    print(f"Saved article to {output_path}")
    
    return {
        "success": True,
        "url": url,
        "title": title,
        "output_file": output_path
    }

def crawl_coindesk(start_url: str = COINDESK_CONFIG["base_url"], max_articles: int = 10, 
                  max_sections: int = 5, output_dir: str = "articles") -> Dict[str, Any]:
    """
    Crawl CoinDesk starting from the given URL, scraping articles and following section links.
    
    Args:
        start_url: URL to start crawling from
        max_articles: Maximum number of articles to scrape
        max_sections: Maximum number of section pages to visit
        output_dir: Directory to save scraped articles
        
    Returns:
        Dictionary with crawling results
    """
    # Check Selenium availability first
    if not check_selenium_availability():
        print("Warning: Proceeding without Selenium. Content extraction may be limited.")
    
    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(output_dir, f"coindesk_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Starting CoinDesk crawler at {start_url}")
    print(f"Saving articles to {output_dir}")
    
    # Initialize tracking variables
    visited_urls = set()
    section_queue = [(start_url, "section")]
    sections_visited = 0
    articles_scraped = 0
    results = []
    
    # First, get section links from the home page
    if start_url == COINDESK_CONFIG["base_url"]:
        print("Scanning homepage for sections...")
        homepage_links = get_page_links(start_url, visited_urls)
        
        # Add section links to the queue
        for url, link_type in homepage_links:
            if link_type == "section" and url not in [s[0] for s in section_queue]:
                section_queue.append((url, link_type))
    
    # Process sections and articles
    while section_queue and sections_visited < max_sections and articles_scraped < max_articles:
        current_url, link_type = section_queue.pop(0)
        
        if link_type == "section":
            print(f"Exploring section: {current_url}")
            sections_visited += 1
            
            # Get links from the section page
            section_links = get_page_links(current_url, visited_urls)
            
            # Process article links first
            for url, l_type in section_links:
                if l_type == "article" and articles_scraped < max_articles:
                    result = scrape_article(url, output_dir)
                    results.append(result)
                    if result["success"]:
                        articles_scraped += 1
                elif l_type == "section" and url not in [s[0] for s in section_queue]:
                    section_queue.append((url, l_type))
    
    # Save a summary file
    summary_filepath = os.path.join(output_dir, "summary.json")
    summary = {
        "start_url": start_url,
        "timestamp": timestamp,
        "sections_visited": sections_visited,
        "articles_scraped": articles_scraped,
        "success_count": sum(1 for r in results if r.get("success", False)),
        "results": results
    }
    
    with open(summary_filepath, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nCrawling summary:")
    print(f"Sections visited: {sections_visited}")
    print(f"Articles scraped: {articles_scraped}")
    print(f"Successfully scraped: {sum(1 for r in results if r.get('success', False))}")
    print(f"Results saved to: {output_dir}")
    
    return summary

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="CoinDesk Custom Crawler")
    parser.add_argument("--start-url", default=COINDESK_CONFIG["base_url"],
                        help="URL to start crawling from (default: CoinDesk homepage)")
    parser.add_argument("--max-articles", type=int, default=10,
                        help="Maximum number of articles to scrape")
    parser.add_argument("--max-sections", type=int, default=5,
                        help="Maximum number of section pages to visit")
    parser.add_argument("--output-dir", default="articles",
                        help="Base directory to save scraped articles")
    
    args = parser.parse_args()
    
    crawl_coindesk(
        start_url=args.start_url,
        max_articles=args.max_articles,
        max_sections=args.max_sections,
        output_dir=args.output_dir
    )

if __name__ == "__main__":
    main() 