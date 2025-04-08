#!/usr/bin/env python3
"""
Enhanced Subpage Crawler

This script combines our existing BS4 crawler with Selenium capabilities
to better handle JavaScript-rendered sites like CoinDesk.
"""

import os
import sys
import json
import time
import re
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin
import random
import requests
from bs4 import BeautifulSoup

# Import functions from existing crawlers
from bs_crawler import (
    extract_title, extract_author, extract_date, extract_description,
    extract_featured_image, html_to_markdown, clean_markdown, create_markdown_filename
)

# Try to import selenium components
try:
    # Import selenium_crawler if available
    from selenium_crawler import (
        SELENIUM_AVAILABLE, WEBDRIVER_MANAGER_AVAILABLE,
        setup_selenium_driver, scrape_with_selenium,
        extract_coindesk_content, extract_generic_content
    )
except ImportError:
    SELENIUM_AVAILABLE = False
    WEBDRIVER_MANAGER_AVAILABLE = False

# Constants for site-specific configurations
SITE_CONFIGS = {
    "coindesk.com": {
        "use_selenium": True,
        "article_patterns": ["/markets/", "/business/", "/tech/", "/policy/", 
                           "/consensus/", "/opinion/", "/finance/"],
        "year_pattern": r"/20\d{2}/\d{2}/\d{2}/",
        "main_content_selector": "article",
        "delay_range": (1, 3),  # (min_seconds, max_seconds)
    },
    "crypto.news": {
        "use_selenium": False,
        "article_patterns": ["/news/", "/feature/", "/follow-up/", "/explained/", "/interview/"],
        "year_pattern": None,
        "main_content_selector": "article",
        "delay_range": (0.5, 2),
    },
    # Add more sites as needed
}

def get_site_config(url: str) -> Dict[str, Any]:
    """
    Get site-specific configuration based on URL domain.
    
    Args:
        url: The URL of the article
        
    Returns:
        Site configuration dictionary
    """
    domain = urlparse(url).netloc.replace("www.", "")
    
    # Return site-specific config if available, otherwise return default config
    return SITE_CONFIGS.get(domain, {
        "use_selenium": False,
        "article_patterns": [],
        "year_pattern": None,
        "main_content_selector": "article",
        "delay_range": (1, 2),
    })

def make_request(url: str, headers=None) -> Optional[Tuple[str, requests.Response]]:
    """
    Make an HTTP request with proper error handling.
    
    Args:
        url: URL to request
        headers: Optional request headers
        
    Returns:
        Tuple of (HTML content, Response object) or None if request failed
    """
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }
    
    if headers:
        default_headers.update(headers)
    
    try:
        response = requests.get(url, headers=default_headers, timeout=10)
        response.raise_for_status()
        return response.text, response
    except requests.RequestException as e:
        print(f"Error requesting {url}: {e}")
        return None
    
def get_article_links(url: str, max_articles: int = 5) -> List[str]:
    """
    Extract article links from a news site's homepage.
    
    Args:
        url: URL of the site homepage
        max_articles: Maximum number of articles to extract
        
    Returns:
        List of article URLs
    """
    site_config = get_site_config(url)
    article_patterns = site_config["article_patterns"]
    year_pattern = site_config["year_pattern"]
    use_selenium = site_config["use_selenium"] and SELENIUM_AVAILABLE
    
    print(f"Extracting article links from {url}")
    
    # Use Selenium if configured and available
    if use_selenium:
        print("Using Selenium for link extraction...")
        driver = setup_selenium_driver()
        if driver:
            try:
                driver.get(url)
                time.sleep(3)  # Wait for page to load
                html_content = driver.page_source
            finally:
                driver.quit()
        else:
            print("Selenium not available, falling back to requests")
            result = make_request(url)
            if not result:
                return []
            html_content, _ = result
    else:
        # Use regular requests
        result = make_request(url)
        if not result:
            return []
        html_content, _ = result
    
    # Parse HTML
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Find all links
    article_links = []
    base_domain = urlparse(url).netloc
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    for link in soup.find_all("a", href=True):
        href = link["href"]
        
        # Resolve relative URLs
        if href.startswith("/"):
            full_url = urljoin(base_url, href)
        elif href.startswith("http"):
            full_url = href
        else:
            continue
            
        # Skip if not from the same domain
        if urlparse(full_url).netloc != base_domain:
            continue
            
        # Apply site-specific filtering
        if article_patterns:
            matches_pattern = any(pattern in full_url for pattern in article_patterns)
            if not matches_pattern:
                continue
                
        # Check for year in URL if pattern specified
        if year_pattern and not re.search(year_pattern, full_url):
            continue
            
        # Avoid duplicates
        if full_url not in article_links:
            article_links.append(full_url)
            
        # Stop if we have enough articles
        if len(article_links) >= max_articles:
            break
    
    print(f"Found {len(article_links)} article links")
    return article_links[:max_articles]

def scrape_article(url: str, output_dir: str) -> Dict[str, Any]:
    """
    Scrape an article and save it as markdown.
    
    Args:
        url: URL of the article
        output_dir: Directory to save the article
        
    Returns:
        Dictionary with scraping results
    """
    site_config = get_site_config(url)
    use_selenium = site_config["use_selenium"] and SELENIUM_AVAILABLE
    delay_range = site_config["delay_range"]
    
    print(f"Scraping article: {url}")
    
    # Apply rate limiting
    time.sleep(random.uniform(delay_range[0], delay_range[1]))
    
    if use_selenium:
        print(f"Using Selenium for {url}")
        result = scrape_with_selenium(url)
        if not result:
            print(f"Selenium scraping failed for {url}, falling back to regular mode")
            use_selenium = False
    
    if not use_selenium:
        # Use regular Beautiful Soup scraping
        response = make_request(url)
        if not response:
            return {"success": False, "url": url, "error": "Failed to load the article"}
            
        html_content, resp = response
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract metadata
        title = extract_title(soup)
        date = extract_date(soup)
        author = extract_author(soup)
        description = extract_description(soup)
        image = extract_featured_image(soup, url)
        
        # Extract main content based on site config
        if "coindesk.com" in url:
            main_content = extract_coindesk_content(soup)
        else:
            main_content = extract_generic_content(soup)
            
        if not main_content:
            # Try to find article content with a more aggressive approach
            for selector in ["article", "main", ".post-content", ".article-content"]:
                main_content = soup.select_one(selector)
                if main_content:
                    break
        
        if not main_content:
            return {"success": False, "url": url, "error": "Could not extract article content"}
            
        # Convert to markdown
        markdown_content = html_to_markdown(str(main_content))
        markdown_content = clean_markdown(markdown_content)
        
        result = {
            "metadata": {
                "title": title,
                "date": date,
                "author": author,
                "description": description,
                "image": image,
                "url": url,
                "source": urlparse(url).netloc.replace("www.", ""),
                "scraped_at": datetime.now().isoformat()
            },
            "markdown": markdown_content
        }
    
    # Create output filename
    filename = create_markdown_filename(url, result["metadata"].get("title", ""))
    output_path = os.path.join(output_dir, filename)
    
    # Save as markdown
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
    
    return {
        "success": True,
        "url": url,
        "title": result["metadata"].get("title", ""),
        "output_file": filename
    }

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Enhanced web crawler for JS-rendered sites")
    parser.add_argument("url", help="URL of the site to crawl")
    parser.add_argument("--max", type=int, default=5, help="Maximum number of articles to scrape")
    parser.add_argument("--force-selenium", action="store_true", help="Force using Selenium even if not configured for site")
    parser.add_argument("--output-dir", help="Custom output directory")
    
    args = parser.parse_args()
    
    # Check if Selenium is available if forced
    if args.force_selenium and not SELENIUM_AVAILABLE:
        print("Error: Selenium is required but not available")
        print("Please install: pip install selenium webdriver-manager")
        return 1
    
    # Extract site domain for output directory
    domain = urlparse(args.url).netloc.replace("www.", "").replace(".", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create output directory
    output_dir = args.output_dir or os.path.join("scraped_articles", f"{domain}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving articles to {output_dir}")
    
    # Get article links
    article_links = get_article_links(args.url, args.max)
    
    if not article_links:
        print("No article links found")
        return 1
    
    # Scrape each article
    results = []
    for i, url in enumerate(article_links, 1):
        print(f"Scraping article {i}/{len(article_links)}")
        result = scrape_article(url, output_dir)
        results.append(result)
    
    # Save summary
    summary = {
        "url": args.url,
        "timestamp": timestamp,
        "articles_found": len(article_links),
        "articles_scraped": sum(1 for r in results if r.get("success", False)),
        "results": results
    }
    
    with open(os.path.join(output_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    
    print("\nScraping summary:")
    print(f"Articles found: {len(article_links)}")
    print(f"Articles scraped: {sum(1 for r in results if r.get('success', False))}")
    print(f"Output directory: {output_dir}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 