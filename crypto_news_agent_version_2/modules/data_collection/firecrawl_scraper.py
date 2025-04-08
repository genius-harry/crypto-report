import os
import json
import html2text
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from firecrawl import FirecrawlApp  # Using the official Firecrawl client

# Load environment variables
load_dotenv()

def get_firecrawl_api_key():
    """Get Firecrawl API key from environment variable."""
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY environment variable not set")
    return api_key

def scrape_article(url: str, api_key: str = None) -> Optional[Dict[str, Any]]:
    """
    Scrape a single article URL using Firecrawl client.
    
    Args:
        url: URL of the article to scrape
        api_key: Firecrawl API key (if not provided, will fetch from env variables)
        
    Returns:
        Dict with scraped content or None if scraping failed
    """
    if api_key is None:
        api_key = get_firecrawl_api_key()
    
    try:
        # Initialize Firecrawl client
        app = FirecrawlApp(api_key=api_key)
        
        # Use the minimal working example from the documentation
        response = app.scrape_url(
            url=url, 
            params={
                'formats': ['markdown'],
            }
        )
        
        # Add metadata to the response
        result = response
        result["metadata"] = {
            "url": url,
            "scraped_at": datetime.now().isoformat()
        }
        
        return result
    
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def extract_markdown_content(scrape_result: Dict[str, Any]) -> Optional[str]:
    """
    Extract markdown content from Firecrawl scrape result.
    If markdown is not available, convert HTML to markdown.
    
    Args:
        scrape_result: Result from Firecrawl's scrape operation
        
    Returns:
        Markdown content or None if extraction failed
    """
    try:
        # First try to get markdown from result if available
        if "markdown" in scrape_result:
            return scrape_result["markdown"]
            
        # Otherwise, try to convert HTML to markdown if HTML is available
        if "html" in scrape_result:
            # Convert HTML to markdown
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            h.ignore_tables = False
            markdown_content = h.handle(scrape_result["html"])
            return markdown_content
        
        # If neither markdown nor HTML is available
        return None
    
    except Exception as e:
        print(f"Error extracting markdown content: {e}")
        return None

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
        import re
        clean_title = re.sub(r'[^\w\s-]', '', title.lower())
        clean_title = re.sub(r'[\s-]+', '_', clean_title)
        clean_title = clean_title[:50]  # Limit length
        return f"{timestamp}_{clean_title}.md"
    
    # If no title, extract domain from URL
    from urllib.parse import urlparse
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
    timestamped_dir = os.path.join(base_dir, f"news_{timestamp}")
    
    # Create the directory if it doesn't exist
    if not os.path.exists(timestamped_dir):
        os.makedirs(timestamped_dir)
        print(f"Created timestamped markdown directory: {timestamped_dir}")
    
    return timestamped_dir

def scrape_and_save_articles(articles: List[Dict[str, Any]], markdown_dir: str = "markdown") -> List[Dict[str, Any]]:
    """
    Scrape articles using Firecrawl and save as markdown files.
    
    Args:
        articles: List of article dictionaries (must contain 'url' and optionally 'title')
        markdown_dir: Directory to save markdown files
        
    Returns:
        List of dictionaries with article info and scrape status
    """
    # Create timestamp directory inside markdown_dir
    timestamped_dir = get_timestamped_markdown_dir(markdown_dir)
    
    api_key = get_firecrawl_api_key()
    results = []
    
    for i, article in enumerate(articles):
        url = article.get("url")
        if not url:
            print(f"Skipping article {i+1} - No URL found")
            continue
            
        title = article.get("title", "")
        print(f"Scraping article {i+1}/{len(articles)}: {title or url}")
        
        # Scrape the article
        scrape_result = scrape_article(url, api_key)
        
        # Process the result
        if scrape_result:
            # Extract markdown content
            markdown_content = extract_markdown_content(scrape_result)
            
            if markdown_content:
                # Create a filename
                filename = create_markdown_filename(url, title)
                filepath = os.path.join(timestamped_dir, filename)
                
                # Save the markdown content
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n\n")
                    f.write(f"Source: {url}\n\n")
                    f.write(markdown_content)
                
                # Add to results
                results.append({
                    "url": url,
                    "title": title,
                    "scraped_at": datetime.now().isoformat(),
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
            
        # Add a small delay to avoid API rate limits
        import time
        time.sleep(1)
    
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
    filename = f"{output_dir}/firecrawl_results_{timestamp}.json"
    
    # Save results to file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"Saved scraping results to {filename}")
    return filename

def main():
    """Main entry point for Firecrawl scraper."""
    import sys
    
    # Set up paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "data")
    markdown_dir = os.path.join(project_root, "markdown")
    
    # Check if an input file is provided
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # Find the most recent top articles file
        top_article_files = [f for f in os.listdir(data_dir) if f.startswith("top_articles_")]
        if not top_article_files:
            print("No top articles file found. Please run the search and selection first.")
            return 1
            
        # Sort by creation time (newest first)
        top_article_files.sort(key=lambda x: os.path.getmtime(os.path.join(data_dir, x)), reverse=True)
        input_file = os.path.join(data_dir, top_article_files[0])
    
    print(f"Processing file: {input_file}")
    
    try:
        # Load articles from file
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Get articles list
        articles = data.get("top_articles", [])
        if not articles:
            print("No articles found in the input file.")
            return 1
            
        print(f"Found {len(articles)} articles to scrape.")
        
        # Scrape and save articles
        results = scrape_and_save_articles(articles, markdown_dir)
        
        # Save results
        save_scrape_results(results, data_dir)
        
        # Print summary
        success_count = sum(1 for r in results if r.get("success", False))
        print(f"\nScraping complete: {success_count}/{len(results)} articles successfully scraped and saved as markdown.")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())