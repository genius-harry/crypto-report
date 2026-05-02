"""
Custom Web Crawler using Beautiful Soup

This module implements a custom web crawler for crypto news articles using
Beautiful Soup instead of Firecrawl. It attempts to extract similar information
with a focus on content extraction quality.
"""

import os
import json
import time
import requests
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import html2text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 15  # seconds
RATE_LIMIT_DELAY = 1  # seconds between requests for same domain
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

# Track the last request time per domain for rate limiting
last_request_time = {}

def wait_for_rate_limit(url: str):
    """
    Wait for rate limit to be reset if needed for a specific domain.
    
    Args:
        url: URL to check for rate limiting
    """
    domain = urlparse(url).netloc
    current_time = time.time()
    
    if domain in last_request_time:
        time_since_last_request = current_time - last_request_time[domain]
        
        if time_since_last_request < RATE_LIMIT_DELAY:
            # Need to wait to respect rate limit
            wait_time = RATE_LIMIT_DELAY - time_since_last_request
            print(f"Rate limiting: Waiting {wait_time:.2f} seconds before next request to {domain}...")
            time.sleep(wait_time)
    
    # Update the last request time
    last_request_time[domain] = time.time()

def scrape_article(url: str, retry_count: int = 2) -> Optional[Dict[str, Any]]:
    """
    Scrape a single article URL using Beautiful Soup.
    
    Args:
        url: URL of the article to scrape
        retry_count: Number of times to retry if the request fails
        
    Returns:
        Dict with scraped content or None if scraping failed
    """
    try:
        # Respect rate limiting
        wait_for_rate_limit(url)
        
        # Make request to the URL
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Get the HTML content
        html_content = response.text
        
        # Parse the HTML content
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract metadata and content
        result = extract_article_data(soup, url)
        
        # Add scraping metadata
        result["metadata"]["url"] = url
        result["metadata"]["scraped_at"] = datetime.now().isoformat()
        result["html"] = html_content  # Store original HTML
        
        return result
        
    except requests.RequestException as e:
        print(f"Request error scraping {url}: {e}")
        if retry_count > 0:
            print(f"Retrying... ({retry_count} attempts left)")
            time.sleep(2)  # Wait before retry
            return scrape_article(url, retry_count - 1)
        return None
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def extract_article_data(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    """
    Extract article data from BeautifulSoup object.
    
    Args:
        soup: BeautifulSoup object for the article page
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
    
    # Extract main content
    main_content_html = extract_main_content(soup)
    result["content"] = clean_text(main_content_html.get_text(" ", strip=True)) if main_content_html else ""
    
    # Convert to markdown
    if main_content_html:
        result["markdown"] = html_to_markdown(str(main_content_html))
    
    return result

def extract_title(soup: BeautifulSoup) -> str:
    """Extract the article title."""
    # Check for Open Graph title
    og_title = soup.find("meta", property="og:title")
    if og_title:
        return og_title.get("content", "").strip()
    
    # Check standard title tag
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.text.strip()
    
    # Check h1 tags
    h1 = soup.find("h1")
    if h1:
        return h1.text.strip()
    
    return ""

def extract_date(soup: BeautifulSoup) -> str:
    """Extract the article publication date."""
    # Check for standard meta tags
    for meta_name in ["article:published_time", "date", "article:modified_time", "datePublished", "dateModified"]:
        meta = soup.find("meta", property=meta_name) or soup.find("meta", attrs={"name": meta_name})
        if meta and meta.get("content"):
            return meta.get("content").strip()
    
    # Check for time elements
    time_elem = soup.find("time")
    if time_elem and time_elem.get("datetime"):
        return time_elem.get("datetime").strip()
    elif time_elem:
        return time_elem.text.strip()
    
    # Look for common date patterns in text
    date_patterns = [
        r'(?:Published|Posted|Updated)(?:\s+on)?\s+(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\d{1,2}\s+\w+\s+\d{4})',
    ]
    
    for pattern in date_patterns:
        for element in soup.find_all(["span", "div", "p"]):
            match = re.search(pattern, element.text)
            if match:
                return match.group(1).strip()
    
    return ""

def extract_author(soup: BeautifulSoup) -> str:
    """Extract the article author."""
    # Check for standard meta tags
    for meta_name in ["author", "article:author", "byline"]:
        meta = soup.find("meta", property=meta_name) or soup.find("meta", attrs={"name": meta_name})
        if meta and meta.get("content"):
            return meta.get("content").strip()
    
    # Check common author elements
    for class_pattern in ["author", "byline", "writer", "contributor"]:
        author_elem = soup.find(["a", "span", "div", "p"], class_=re.compile(class_pattern, re.I))
        if author_elem:
            # Clean up the text (remove "By" or other prefixes)
            author_text = author_elem.text.strip()
            author_text = re.sub(r'^[Bb]y\s+', '', author_text)
            return author_text
    
    return ""

def extract_description(soup: BeautifulSoup) -> str:
    """Extract the article description or summary."""
    # Check for Open Graph description
    og_desc = soup.find("meta", property="og:description")
    if og_desc:
        return og_desc.get("content", "").strip()
    
    # Check standard meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc:
        return meta_desc.get("content", "").strip()
    
    # Check for article summary/description elements
    for class_pattern in ["summary", "description", "excerpt", "intro", "standfirst"]:
        desc_elem = soup.find(["div", "p", "section"], class_=re.compile(class_pattern, re.I))
        if desc_elem:
            return desc_elem.text.strip()
    
    return ""

def extract_featured_image(soup: BeautifulSoup, base_url: str) -> str:
    """Extract the featured image URL."""
    # Check for Open Graph image
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        return make_absolute_url(og_image.get("content"), base_url)
    
    # Check for Twitter image
    twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
    if twitter_image and twitter_image.get("content"):
        return make_absolute_url(twitter_image.get("content"), base_url)
    
    # Look for featured image in content
    for class_pattern in ["featured", "hero", "main", "lead", "thumbnail"]:
        img = soup.find(["img", "figure"], class_=re.compile(class_pattern, re.I))
        if img:
            # If it's a figure, look for img inside
            if img.name == "figure" and img.find("img"):
                img = img.find("img")
            
            src = img.get("src") or img.get("data-src")
            if src:
                return make_absolute_url(src, base_url)
    
    # Fallback to first image in article
    main_content = extract_main_content(soup)
    if main_content:
        img = main_content.find("img")
        if img and (img.get("src") or img.get("data-src")):
            return make_absolute_url(img.get("src") or img.get("data-src"), base_url)
    
    return ""

def extract_main_content(soup: BeautifulSoup) -> Optional[BeautifulSoup]:
    """
    Extract the main content of the article.
    Returns a BeautifulSoup object containing the main content.
    """
    # Get the domain to apply site-specific extraction
    domain = ""
    try:
        # Try to extract domain from OpenGraph URL
        og_url = soup.find("meta", property="og:url")
        if og_url and og_url.get("content"):
            from urllib.parse import urlparse
            domain = urlparse(og_url.get("content")).netloc
    except:
        pass
    
    # Site-specific extraction for CoinDesk
    if "coindesk.com" in domain:
        # CoinDesk specific article content extraction
        # First try the main article container
        article_content = soup.find("div", class_="at-content-wrapper")
        
        if not article_content:
            # Try another common container for CoinDesk articles
            article_content = soup.find(["article", "div"], class_=re.compile(r"article|story|post-content", re.I))
        
        if article_content:
            # Clean up the content
            for tag in article_content.find_all(["script", "style", "nav", "header", "footer", 
                                         "aside", "form", "iframe", "noscript", "div"],
                                       class_=re.compile(r"ad-|ad_|promo|newsletter|subscription|signup|related|comments|social", re.I)):
                tag.decompose()
            
            return article_content
    
    # Regular extraction for other sites
    # First try to find article or main content by common containers
    content_containers = [
        soup.find("article"),
        soup.find(["div", "section"], class_=re.compile(r"article|post|entry|content|body", re.I)),
        soup.find(id=re.compile(r"article|post|entry|content|body", re.I)),
        soup.find("main"),
    ]
    
    # Use the first non-None container
    content = next((c for c in content_containers if c is not None), None)
    
    if not content:
        # Fallback: try to find the div with the most paragraph tags
        p_counts = {}
        for div in soup.find_all("div"):
            p_counts[div] = len(div.find_all("p"))
        
        if p_counts:
            content = max(p_counts.items(), key=lambda x: x[1])[0]
    
    if content:
        # Clean up the content
        for tag in content.find_all(["script", "style", "nav", "header", "footer", 
                                     "aside", "form", "iframe", "noscript"]):
            tag.decompose()
        
        # Remove comment sections
        for tag in content.find_all(["div", "section"], 
                                   class_=re.compile(r"comment|disqus|share|social|related|sidebar", re.I)):
            tag.decompose()
        
        return content
    
    return None

def html_to_markdown(html_content: str) -> str:
    """Convert HTML content to markdown format."""
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = False
    converter.ignore_tables = False
    converter.body_width = 0  # Don't wrap text
    
    markdown_content = converter.handle(html_content)
    
    # Clean up the markdown
    markdown_content = clean_markdown(markdown_content)
    
    return markdown_content

def clean_markdown(markdown_content: str) -> str:
    """Clean up markdown content."""
    # Remove excessive newlines
    markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
    
    # Fix image paths to ensure they're using https
    markdown_content = re.sub(r'!\[.*?\]\(//', '![](https://', markdown_content)
    
    return markdown_content

def clean_text(text: str) -> str:
    """Clean up text content."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove UTF control characters
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
    
    return text.strip()

def make_absolute_url(url: str, base_url: str) -> str:
    """Convert a relative URL to an absolute URL."""
    if url.startswith('http'):
        return url
    elif url.startswith('//'):
        return 'https:' + url
    else:
        return urljoin(base_url, url)

def create_markdown_filename(url: str, title: str = None) -> str:
    """
    Create a suitable filename for a markdown file based on URL and title.
    
    Args:
        url: Article URL
        title: Article title (optional)
        
    Returns:
        A safe filename ending with .md
    """
    # Start with timestamp for uniqueness
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # If title is available, use it (cleaned)
    if title:
        # Clean the title: lowercase, replace spaces with underscores, keep only alphanumeric and some special chars
        clean_title = re.sub(r'[^\w\s-]', '', title.lower())
        clean_title = re.sub(r'[\s-]+', '_', clean_title)
        clean_title = clean_title[:50]  # Limit length
        return f"{timestamp}_{clean_title}.md"
    
    # If no title, extract domain from URL
    domain = urlparse(url).netloc.replace('www.', '')
    return f"{timestamp}_{domain}.md"

def get_timestamped_markdown_dir(base_dir="markdown"):
    """
    Create a time-stamped directory for markdown files.
    
    Args:
        base_dir (str): Base directory for markdown files
        
    Returns:
        str: Path to the time-stamped directory
    """
    # Create base directory if it doesn't exist
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    
    # Create a timestamped directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_dir = os.path.join(base_dir, f"bs_news_{timestamp}")
    
    # Create the directory if it doesn't exist
    if not os.path.exists(timestamped_dir):
        os.makedirs(timestamped_dir)
        print(f"Created timestamped markdown directory: {timestamped_dir}")
    
    return timestamped_dir

def scrape_and_save_articles(articles: List[Dict[str, Any]], markdown_dir: str = "markdown") -> List[Dict[str, Any]]:
    """
    Scrape articles using Beautiful Soup and save as markdown files.
    
    Args:
        articles: List of article dictionaries (must contain 'url' and optionally 'title')
        markdown_dir: Directory to save markdown files
        
    Returns:
        List of dictionaries with article info and scrape status
    """
    # Create timestamp directory inside markdown_dir
    timestamped_dir = get_timestamped_markdown_dir(markdown_dir)
    results = []
    
    for i, article in enumerate(articles):
        url = article.get("url")
        if not url:
            print(f"Skipping article {i+1} - No URL found")
            continue
            
        title = article.get("title", "")
        print(f"Scraping article {i+1}/{len(articles)}: {title or url}")
        
        # Scrape the article
        scrape_result = scrape_article(url)
        
        # Process the result
        if scrape_result:
            # Get markdown content
            markdown_content = scrape_result.get("markdown", "")
            
            if markdown_content:
                # Create a filename
                filename = create_markdown_filename(url, scrape_result["metadata"].get("title", title))
                filepath = os.path.join(timestamped_dir, filename)
                
                # Save the markdown content
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"# {scrape_result['metadata'].get('title', title)}\n\n")
                    
                    # Add metadata
                    f.write(f"Source: {url}\n")
                    if scrape_result["metadata"].get("author"):
                        f.write(f"Author: {scrape_result['metadata']['author']}\n")
                    if scrape_result["metadata"].get("date"):
                        f.write(f"Date: {scrape_result['metadata']['date']}\n")
                    f.write("\n")
                    
                    # Write the main content
                    f.write(markdown_content)
                
                # Add to results
                results.append({
                    "url": url,
                    "title": scrape_result["metadata"].get("title", title),
                    "author": scrape_result["metadata"].get("author", ""),
                    "date": scrape_result["metadata"].get("date", ""),
                    "scraped_at": scrape_result["metadata"].get("scraped_at", ""),
                    "markdown_file": filepath,
                    "success": True
                })
                
                print(f"  ✅ Saved to {filepath}")
            else:
                results.append({
                    "url": url,
                    "title": title,
                    "scraped_at": datetime.now().isoformat(),
                    "success": False,
                    "error": "Failed to extract markdown content"
                })
                print(f"  ❌ Failed to extract markdown content")
        else:
            results.append({
                "url": url,
                "title": title,
                "scraped_at": datetime.now().isoformat(),
                "success": False,
                "error": "Failed to scrape URL"
            })
            print(f"  ❌ Failed to scrape URL")
            
    # Save a summary file in the timestamped directory
    summary_filepath = os.path.join(timestamped_dir, "summary.json")
    with open(summary_filepath, "w", encoding="utf-8") as f:
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_articles": len(articles),
            "success_count": sum(1 for r in results if r.get("success", False)),
            "articles": results,
        }
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"Saved summary to {summary_filepath}")
    
    return results

def save_scrape_results(results: List[Dict[str, Any]], output_dir: str = "data"):
    """Save scraping results to a JSON file."""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create filename based on timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/bs_crawler_results_{timestamp}.json"
    
    # Save results to file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"Saved results to {filename}")
    return filename

def main():
    """Main entry point for BS crawler."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape articles using Beautiful Soup")
    parser.add_argument("--urls", nargs="+", help="URLs to scrape")
    parser.add_argument("--url-file", help="File containing URLs to scrape (one per line)")
    parser.add_argument("--output-dir", default="markdown", help="Output directory for markdown files")
    parser.add_argument("--data-dir", default="data", help="Output directory for JSON data")
    
    args = parser.parse_args()
    
    # Get URLs to scrape
    urls = []
    if args.urls:
        urls = [{"url": url} for url in args.urls]
    elif args.url_file:
        with open(args.url_file, "r", encoding="utf-8") as f:
            urls = [{"url": line.strip()} for line in f if line.strip()]
    
    if not urls:
        print("No URLs to scrape. Please provide URLs using --urls or --url-file")
        return
    
    print(f"Scraping {len(urls)} URLs...")
    results = scrape_and_save_articles(urls, args.output_dir)
    save_scrape_results(results, args.data_dir)
    
    print(f"Successfully scraped {sum(1 for r in results if r.get('success', False))}/{len(urls)} articles")
    
if __name__ == "__main__":
    main() 