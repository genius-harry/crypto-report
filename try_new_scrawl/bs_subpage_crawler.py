#!/usr/bin/env python3
"""
Subpage Crawler using Beautiful Soup

This script extends the basic crawler to handle websites with multiple subpages,
like news sites with multiple articles.
"""

import os
import json
import time
import requests
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import html2text

from bs_crawler import (
    HEADERS, REQUEST_TIMEOUT, wait_for_rate_limit, 
    scrape_article, extract_article_data, create_markdown_filename
)

def get_article_links(url: str, max_links: int = 10) -> List[str]:
    """
    Extract article links from a website's main page.
    
    Args:
        url: The main page URL to crawl
        max_links: Maximum number of links to extract
        
    Returns:
        List of article URLs
    """
    try:
        # Respect rate limiting
        wait_for_rate_limit(url)
        
        # Make request to the URL
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Get the base URL for resolving relative URLs
        base_url = "{0.scheme}://{0.netloc}".format(urlparse(url))
        
        # Extract links based on the website structure
        domain = urlparse(url).netloc
        article_links = []
        visited = set()
        
        # Different patterns for different sites
        if "coindesk.com" in domain:
            # CoinDesk articles typically have these patterns in URLs
            article_patterns = [
                "/markets/", "/tech/", "/policy/", "/business/", 
                "/consensus/", "/opinion/", "/finance/"
            ]
            
            # Make sure we're getting year in URL path for CoinDesk articles
            year_pattern = re.compile(r"/20\d{2}/")
            
            # Find all links on the page
            for link in soup.find_all("a", href=True):
                href = link["href"]
                full_url = urljoin(base_url, href)
                
                # Skip if already processed or not an article
                if full_url in visited:
                    continue
                    
                # CoinDesk articles typically have year in the URL
                if (any(pattern in href for pattern in article_patterns) and 
                    year_pattern.search(href)):
                    article_links.append(full_url)
                    visited.add(full_url)
                    
                    if len(article_links) >= max_links:
                        break
                        
        elif "crypto.news" in domain:
            # Find all news article links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                full_url = urljoin(base_url, href)
                
                # Skip if already processed
                if full_url in visited:
                    continue
                
                # crypto.news articles typically have this structure
                if "/news/" in href or "/feature/" in href or "/follow-up/" in href:
                    article_links.append(full_url)
                    visited.add(full_url)
                    
                    if len(article_links) >= max_links:
                        break
        else:
            # Generic approach for other sites
            # Look for article-like patterns in URLs
            article_patterns = [
                "/article/", "/news/", "/post/", "/story/", 
                "/blog/", "/read/", "/content/"
            ]
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                full_url = urljoin(base_url, href)
                
                # Skip if already processed or not an article or external link
                if full_url in visited or domain not in full_url:
                    continue
                
                # Check if it matches generic article patterns
                if any(pattern in href for pattern in article_patterns):
                    article_links.append(full_url)
                    visited.add(full_url)
                    
                    if len(article_links) >= max_links:
                        break
        
        print(f"Found {len(article_links)} article links on {url}")
        return article_links
        
    except Exception as e:
        print(f"Error extracting links from {url}: {e}")
        return []

def crawl_and_save_site(url: str, max_articles: int = 5, output_dir: str = "scraped_articles") -> List[Dict[str, Any]]:
    """
    Crawl a website, extract article links, and scrape each article.
    
    Args:
        url: The main page URL to crawl
        max_articles: Maximum number of articles to scrape
        output_dir: Directory to save the scraped articles
        
    Returns:
        List of dictionaries with article info and scrape status
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a timestamped subdirectory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    site_name = urlparse(url).netloc.replace("www.", "").replace(".", "_")
    site_dir = os.path.join(output_dir, f"{site_name}_{timestamp}")
    os.makedirs(site_dir, exist_ok=True)
    
    print(f"Created directory: {site_dir}")
    
    # Get article links
    article_links = get_article_links(url, max_links=max_articles)
    
    results = []
    for i, article_url in enumerate(article_links):
        print(f"Scraping article {i+1}/{len(article_links)}: {article_url}")
        
        # Scrape the article
        result = scrape_article(article_url)
        
        # Process the result
        if result:
            # Get title for filename
            title = result["metadata"].get("title", "")
            
            # Create a filename
            filename = create_markdown_filename(article_url, title)
            filepath = os.path.join(site_dir, filename)
            
            # Save the markdown content
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")
                f.write(f"Source: {article_url}\n")
                
                # Add metadata
                for key, value in result["metadata"].items():
                    if key not in ["title", "url"] and value:
                        f.write(f"{key.capitalize()}: {value}\n")
                
                f.write("\n")
                f.write(result.get("markdown", ""))
            
            # Add to results
            results.append({
                "url": article_url,
                "title": title,
                "scraped_at": result["metadata"].get("scraped_at", ""),
                "markdown_file": filepath,
                "success": True
            })
            
            print(f"  ✅ Saved to {filepath}")
        else:
            results.append({
                "url": article_url,
                "scraped_at": datetime.now().isoformat(),
                "success": False,
                "error": "Failed to scrape URL"
            })
            print(f"  ❌ Failed to scrape URL")
    
    # Save a summary file
    summary_filepath = os.path.join(site_dir, "summary.json")
    with open(summary_filepath, "w", encoding="utf-8") as f:
        summary = {
            "site": url,
            "timestamp": datetime.now().isoformat(),
            "total_articles": len(article_links),
            "success_count": sum(1 for r in results if r.get("success", False)),
            "articles": results,
        }
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"Saved summary to {summary_filepath}")
    return results

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Crawl a website with subpages/articles")
    parser.add_argument("url", help="URL of the website to crawl")
    parser.add_argument("--max", type=int, default=5, help="Maximum number of articles to scrape")
    parser.add_argument("--output", default="scraped_articles", help="Output directory")
    
    args = parser.parse_args()
    
    print(f"Crawling {args.url} for up to {args.max} articles...")
    results = crawl_and_save_site(args.url, max_articles=args.max, output_dir=args.output)
    
    success_count = sum(1 for r in results if r.get("success", False))
    print(f"\nSuccessfully scraped {success_count}/{len(results)} articles")

if __name__ == "__main__":
    main() 