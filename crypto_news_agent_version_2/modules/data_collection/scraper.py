"""
Crypto News Scraper Module

This module handles scraping crypto news articles from various sources.
"""

import os
import json
import re
import requests
import time
from typing import Dict, List, Any
from datetime import datetime
from bs4 import BeautifulSoup
import html2text
from dotenv import load_dotenv
import hashlib

# Import custom crawler support
from .custom_crawlers.crawler_controller import run_all_crawlers, collect_scraped_data
from .custom_crawlers import AVAILABLE_CRAWLERS

# Import Firecrawl library (as fallback)
try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    print("Firecrawl library not found. Will use custom crawlers only.")
    FIRECRAWL_AVAILABLE = False

# Load environment variables
load_dotenv()

# API Keys
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

# Rate limiting constants
FIRECRAWL_RATE_LIMIT = 10  # Keep safely under the 11 req/min limit
FIRECRAWL_REQUEST_INTERVAL = 60 / FIRECRAWL_RATE_LIMIT  # seconds between requests

# Track the last request time for rate limiting
last_firecrawl_request_time = 0

def ensure_dir(dir_path: str) -> str:
    """
    Ensure a directory exists.
    
    Args:
        dir_path: Directory path to ensure exists
        
    Returns:
        The directory path
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    return dir_path

def clean_html(html_content: str) -> str:
    """
    Clean HTML content and convert to markdown.
    
    Args:
        html_content: HTML content to clean
        
    Returns:
        Cleaned markdown content
    """
    # Convert HTML to markdown
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = False
    converter.body_width = 0  # No wrapping
    
    markdown = converter.handle(html_content)
    
    # Clean up markdown
    # Remove excessive newlines
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    
    # Fix image paths
    markdown = re.sub(r'!\[.*?\]\(//', '![](https://', markdown)
    
    return markdown

def wait_for_rate_limit():
    """
    Wait for rate limit to be reset if needed.
    """
    global last_firecrawl_request_time
    
    current_time = time.time()
    time_since_last_request = current_time - last_firecrawl_request_time
    
    if time_since_last_request < FIRECRAWL_REQUEST_INTERVAL:
        # Need to wait to respect rate limit
        wait_time = FIRECRAWL_REQUEST_INTERVAL - time_since_last_request
        print(f"Rate limiting: Waiting {wait_time:.2f} seconds before next request...")
        time.sleep(wait_time)
    
    # Update the last request time
    last_firecrawl_request_time = time.time()

def scrape_url_with_firecrawl(url: str) -> Dict[str, Any]:
    """
    Scrape a URL using Firecrawl API.
    
    Args:
        url: URL to scrape
        
    Returns:
        Dictionary containing scraped content
    """
    if not FIRECRAWL_AVAILABLE:
        print(f"Firecrawl not available, using fallback for {url}")
        return {"url": url, "error": "Firecrawl module not available"}
        
    try:
        # Wait for rate limit if needed
        wait_for_rate_limit()
        
        # Initialize Firecrawl client
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
        
        # Make request to Firecrawl
        print(f"Scraping {url} with Firecrawl...")
        response = app.scrape_url(url=url, params={
            'formats': ['markdown'],
        })
        
        # Handle response based on its type
        if isinstance(response, dict):
            # Check if the markdown content is available
            if "markdown" in response:
                # Direct successful response from new API format
                return {
                    "url": url,
                    "title": response.get("metadata", {}).get("title", ""),
                    "date": response.get("metadata", {}).get("date", ""),
                    "author": response.get("metadata", {}).get("author", ""),
                    "description": response.get("metadata", {}).get("description", ""),
                    "content": response.get("markdown", ""),
                    "markdown": response.get("markdown", ""),
                    "image": response.get("metadata", {}).get("image", ""),
                    "source": url.split("//")[-1].split("/")[0].replace("www.", "")
                }
            # Old API format response with success field 
            elif 'success' in response and response.get('success'):
                content = response.get("data", {})
                
                return {
                    "url": url,
                    "title": content.get("title", ""),
                    "date": content.get("date", ""),
                    "author": content.get("author", ""),
                    "description": content.get("description", ""),
                    "content": content.get("text", ""),
                    "markdown": content.get("markdown", ""),
                    "image": content.get("image", ""),
                    "source": url.split("//")[-1].split("/")[0].replace("www.", "")
                }
            # Check for rate limit error
            elif 'message' in response and 'rate limit' in response.get('message', '').lower():
                error_msg = response.get('message', 'Rate limit exceeded')
                print(f"Rate limit exceeded for {url}: {error_msg}")
                print("Waiting 60 seconds before retrying...")
                time.sleep(60)  # Wait a full minute before retrying
                
                # Try again after waiting
                return scrape_url_with_firecrawl(url)
            else:
                error_msg = response.get('message', 'Unknown error')
                print(f"Failed to scrape {url}: {error_msg}")
                return {"url": url, "error": error_msg}
        else:
            # Unexpected response type
            print(f"Unexpected response type from Firecrawl for {url}: {type(response)}")
            return {"url": url, "error": f"Unexpected response type: {type(response)}"}
    except Exception as e:
        print(f"Error scraping {url} with Firecrawl: {e}")
        
        # Check if it's a rate limit error
        if 'rate limit' in str(e).lower():
            print("Rate limit error detected. Waiting 60 seconds before retrying...")
            time.sleep(60)  # Wait a full minute
            return scrape_url_with_firecrawl(url)
            
        print(f"Firecrawl failed, trying requests: {e}")
        return {"url": url, "error": str(e)}

def scrape_url_with_requests(url: str) -> Dict[str, Any]:
    """
    Scrape a URL using requests and BeautifulSoup.
    
    Args:
        url: URL to scrape
        
    Returns:
        Dictionary containing scraped content
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract title
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.text.strip()
        
        # Extract meta description
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content", "")
        
        # Extract publication date
        date = ""
        date_meta = soup.find("meta", property="article:published_time")
        if date_meta:
            date = date_meta.get("content", "")
        else:
            # Try common date classes and formats
            date_elem = soup.find(["time", "span", "div"], class_=re.compile(r"date|time|publi|posted", re.I))
            if date_elem:
                date = date_elem.text.strip()
        
        # Extract author
        author = ""
        author_meta = soup.find("meta", property="article:author")
        if author_meta:
            author = author_meta.get("content", "")
        else:
            # Try common author classes
            author_elem = soup.find(["a", "span", "div"], class_=re.compile(r"author|byline|writer", re.I))
            if author_elem:
                author = author_elem.text.strip()
        
        # Extract main content
        content = ""
        article = soup.find(["article", "main", "div"], class_=re.compile(r"article|content|post", re.I))
        if article:
            # Remove scripts, styles, comments, and other unwanted elements
            for element in article.find_all(["script", "style", "meta", "noscript", "iframe"]):
                element.decompose()
            
            content = article.get_text(separator="\n", strip=True)
        else:
            # Fallback to body text
            body = soup.find("body")
            if body:
                for element in body.find_all(["script", "style", "meta", "noscript", "iframe", "header", "footer", "nav"]):
                    element.decompose()
                
                content = body.get_text(separator="\n", strip=True)
        
        # Create markdown from HTML
        markdown = clean_html(article.prettify() if article else body.prettify() if body else response.text)
        
        return {
            "url": url,
            "title": title,
            "date": date,
            "author": author,
            "description": description,
            "content": content,
            "markdown": markdown,
            "source": url.split("//")[-1].split("/")[0].replace("www.", "")
        }
        
    except Exception as e:
        print(f"Error scraping {url} with requests: {e}")
        return {"url": url, "error": str(e)}

def save_article_as_markdown(article: Dict[str, Any], output_dir: str = "markdown") -> str:
    """
    Save the article as a markdown file.
    
    Args:
        article: Article data
        output_dir: Directory to save the markdown file
        
    Returns:
        Path to the saved markdown file
    """
    # Ensure the output directory exists
    ensure_dir(output_dir)
    
    # Create a file name based on the title
    title = article.get("title", "Untitled")
    source = article.get("source", "unknown")
    
    # Sanitize title for filename
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().lower()
    safe_title = re.sub(r'[-\s]+', '-', safe_title)
    
    # Add a timestamp to make the filename unique
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{safe_title[:50]}.md"
    
    # Create the full path
    filepath = os.path.join(output_dir, filename)
    
    # Format the markdown content
    markdown_content = f"# {title}\n\n"
    
    if article.get("date"):
        markdown_content += f"**Date:** {article['date']}\n\n"
    
    if article.get("author"):
        markdown_content += f"**Author:** {article['author']}\n\n"
    
    if article.get("source"):
        markdown_content += f"**Source:** {article['source']}\n\n"
    
    if article.get("url"):
        markdown_content += f"**URL:** {article['url']}\n\n"
    
    markdown_content += "---\n\n"
    
    # Use the markdown content if available, otherwise use the plain text content
    if article.get("markdown"):
        markdown_content += article["markdown"]
    elif article.get("content"):
        markdown_content += article["content"]
    
    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print(f"Saved article to {filepath}")
    return filepath

def scrape_articles(articles: List[Dict[str, Any]], verbose: bool = False, use_custom_crawlers: bool = True, max_articles_per_crawler: int = 15) -> List[Dict[str, Any]]:
    """
    Scrape articles using various methods.
    
    Args:
        articles: List of articles to scrape
        verbose: Whether to print verbose output
        use_custom_crawlers: Whether to use custom crawlers for known sites
        max_articles_per_crawler: Maximum number of articles to fetch per custom crawler
        
    Returns:
        List of scraped articles
    """
    scraped_results = []
    
    # First, try to use custom crawlers for known crypto news sites
    if use_custom_crawlers:
        print("\n=== Using Custom Crawlers for Specialized Sites ===")
        
        # Directory for scraped articles from custom crawlers
        custom_output_dir = "data/scraped_articles"
        ensure_dir(custom_output_dir)
        
        # Run custom crawlers
        crawler_results = run_all_crawlers(AVAILABLE_CRAWLERS, max_articles_per_crawler)
        
        # Collect the scraped data
        custom_scraped_articles = collect_scraped_data(
            [crawler for crawler, success in crawler_results.items() if success],
            custom_output_dir
        )
        
        # Add to results
        scraped_results.extend(custom_scraped_articles)
        
        print(f"Collected {len(custom_scraped_articles)} articles from custom crawlers.")
    
    # Then, process the search results using Firecrawl or requests as fallback
    print("\n=== Processing Search Results ===")
    markdown_dir = ensure_dir("markdown")
    formatted_dir = ensure_dir(os.path.join(markdown_dir, "formatted"))
    
    for i, article in enumerate(articles):
        url = article.get("url", "")
        
        if not url:
            continue
        
        print(f"Processing article {i+1}/{len(articles)}: {url}")
        
        # Skip if we already processed this URL from a custom crawler
        if any(result.get("url") == url for result in scraped_results):
            print(f"Skipping {url} - already processed by custom crawler")
            continue
        
        # Try Firecrawl first if available
        if FIRECRAWL_AVAILABLE and FIRECRAWL_API_KEY:
            result = scrape_url_with_firecrawl(url)
            if "error" not in result or not result["error"]:
                # Successful scrape with Firecrawl
                print(f"Successfully scraped {url} with Firecrawl")
                
                # Save as markdown
                filepath = save_article_as_markdown(result, formatted_dir)
                result["file_path"] = filepath
                
                scraped_results.append(result)
                continue
            else:
                print(f"Firecrawl failed for {url}: {result.get('error', 'Unknown error')}")
        
        # Fallback to requests
        print(f"Trying to scrape {url} with requests...")
        result = scrape_url_with_requests(url)
        
        if "error" not in result or not result["error"]:
            # Successful scrape with requests
            print(f"Successfully scraped {url} with requests")
            
            # Save as markdown
            filepath = save_article_as_markdown(result, formatted_dir)
            result["file_path"] = filepath
            
            scraped_results.append(result)
        else:
            print(f"All scraping methods failed for {url}")
            
            # Add a placeholder with at least the title and URL
            placeholder = {
                "url": url,
                "title": article.get("title", "Unknown Title"),
                "source": article.get("source", url.split("//")[-1].split("/")[0].replace("www.", "")),
                "date": article.get("date", ""),
                "content": f"Failed to scrape content from {url}",
                "error": result.get("error", "Unknown error")
            }
            scraped_results.append(placeholder)
    
    # Save all scraped results to JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ensure_dir("data")
    results_file = os.path.join(output_dir, f"scraped_results_{timestamp}.json")
    
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "count": len(scraped_results),
            "articles": [
                {k: v for k, v in article.items() if k != "content"}  # Exclude full content to keep file smaller
                for article in scraped_results
            ]
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nScraped {len(scraped_results)} articles total")
    print(f"Saved metadata to {results_file}")
    
    return scraped_results 