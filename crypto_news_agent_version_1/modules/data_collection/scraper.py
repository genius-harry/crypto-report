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

# Import Firecrawl library
try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    print("Firecrawl library not found. Will use fallback scraping method.")
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
                content = body.get_text(separator="\n", strip=True)
        
        # Convert content to markdown
        markdown = clean_html(content)
        
        # Extract main image
        image = ""
        og_image = soup.find("meta", property="og:image")
        if og_image:
            image = og_image.get("content", "")
        
        return {
            "url": url,
            "title": title,
            "date": date,
            "author": author,
            "description": description,
            "content": content,
            "markdown": markdown,
            "image": image,
            "source": url.split("//")[-1].split("/")[0].replace("www.", "")
        }
    except Exception as e:
        print(f"Error scraping {url} with requests: {e}")
        return {"url": url, "error": str(e)}

def save_article_as_markdown(article: Dict[str, Any], output_dir: str = "markdown") -> str:
    """
    Save an article as a markdown file.
    
    Args:
        article: Article data
        output_dir: Directory to save to
    
    Returns:
        Path to the saved file
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create a filename from the title
    if article.get("title"):
        filename = re.sub(r'[^\w\s-]', '', article["title"]).strip().lower()
        filename = re.sub(r'[-\s]+', '-', filename)
    else:
        # Use a random name if title is not available
        filename = f"article-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Limit filename length
    if len(filename) > 50:
        filename = filename[:50]
    
    filepath = os.path.join(output_dir, f"{filename}.md")
    
    # Create markdown content
    markdown_content = f"# {article.get('title', 'Untitled')}\n\n"
    
    if article.get("date"):
        markdown_content += f"Date: {article.get('date')}\n\n"
    
    if article.get("author"):
        markdown_content += f"Author: {article.get('author')}\n\n"
    
    if article.get("source"):
        markdown_content += f"Source: {article.get('source')}\n\n"
    
    if article.get("url"):
        markdown_content += f"URL: {article.get('url')}\n\n"
    
    if article.get("description"):
        markdown_content += f"Summary: {article.get('description')}\n\n"
    
    if article.get("image"):
        markdown_content += f"![{article.get('title', 'Image')}]({article.get('image')})\n\n"
    
    if article.get("markdown"):
        markdown_content += article.get("markdown")
    elif article.get("content"):
        markdown_content += article.get("content")
    
    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    return filepath

def scrape_articles(articles: List[Dict[str, Any]], verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Scrape content from a list of articles.
    
    Args:
        articles: List of articles to scrape
        verbose: Whether to print verbose output
        
    Returns:
        List of articles with scraped content
    """
    results = []
    skipped = 0
    
    print(f"Scraping {len(articles)} articles...")
    
    # Create a timestamped folder for markdown files
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M")
    markdown_dir = os.path.join("markdown", f"markdown_{timestamp}")
    ensure_dir(markdown_dir)
    
    if verbose:
        print(f"Created markdown directory: {markdown_dir}")
    
    for i, article in enumerate(articles):
        url = article.get("url", "")
        if not url:
            print(f"Skipping article {i+1}/{len(articles)} - No URL")
            skipped += 1
            continue
        
        print(f"Scraping [{i+1}/{len(articles)}]: {url}")
        
        max_retries = 3
        retry_count = 0
        success = False
        
        while retry_count < max_retries and not success:
            try:
                # Try Firecrawl first
                if FIRECRAWL_AVAILABLE and FIRECRAWL_API_KEY:
                    if verbose:
                        print(f"Using Firecrawl for {url}")
                    scraped = scrape_url_with_firecrawl(url)
                    
                    # Check if Firecrawl failed
                    if "error" in scraped:
                        if verbose:
                            print(f"Firecrawl error: {scraped.get('error')}")
                        # Try fallback with requests
                        print(f"Firecrawl failed, trying requests: {scraped.get('error')}")
                        scraped = scrape_url_with_requests(url)
                        # Add a delay after using requests to prevent overloading servers
                        time.sleep(2)
                else:
                    # Use requests as fallback
                    if verbose:
                        print(f"Using requests for {url} (Firecrawl not available)")
                    scraped = scrape_url_with_requests(url)
                    # Add a delay after using requests to prevent overloading servers
                    time.sleep(2)
                
                success = True
            except Exception as e:
                retry_count += 1
                print(f"Error on attempt {retry_count}/{max_retries} for {url}: {str(e)}")
                if retry_count < max_retries:
                    wait_time = 5 * retry_count  # Exponential backoff
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"Failed to scrape {url} after {max_retries} attempts")
                    scraped = {"url": url, "error": str(e)}
        
        # Check if there's any content
        if not scraped.get("content") and not scraped.get("markdown"):
            print(f"Failed to scrape content from {url}")
            if "error" in scraped:
                print(f"Error: {scraped.get('error')}")
            skipped += 1
            continue
        
        # Add article metadata
        scraped.update({
            "title": article.get("title", scraped.get("title", "")),
            "url": url,
            "source": article.get("source", scraped.get("source", "")),
            "snippet": article.get("snippet", ""),
            "date": article.get("date", scraped.get("date", ""))
        })
        
        # Clean extracted content
        if scraped.get("content"):
            scraped["clean_content"] = clean_html(scraped["content"])
        
        if scraped.get("markdown"):
            scraped["clean_content"] = scraped["markdown"]
        
        # Save as markdown for readability and backward compatibility
        scraped["markdown_file"] = save_article_as_markdown(scraped, markdown_dir)
        if verbose:
            print(f"Saved markdown to {scraped['markdown_file']}")
            
        # Generate summary if needed
        if len(scraped.get("clean_content", "")) > 100:
            # Save to file
            output_dir = os.path.join("data", "articles")
            ensure_dir(output_dir)
            
            article_id = hashlib.md5(url.encode()).hexdigest()[:10]
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"{article_id}_{timestamp}.json"
            
            with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                json.dump(scraped, f, ensure_ascii=False, indent=2)
            
            if verbose:
                print(f"Saved article to {filename}")
            
            results.append(scraped)
        else:
            print(f"Article content too short, skipping: {url}")
            skipped += 1
            
        # Add a small delay between articles regardless of method to be safe
        time.sleep(1)
    
    # Save collection to file
    output_dir = os.path.join("data", "articles")
    ensure_dir(output_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"scraped_articles_{timestamp}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "count": len(results),
            "articles": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"Scraped {len(results)} articles (skipped {skipped})")
    print(f"Saved scraped articles to {output_file}")
    print(f"Saved markdown files to {markdown_dir}")
    
    return results 