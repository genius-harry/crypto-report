#!/usr/bin/env python3
"""
Integration Script for Beautiful Soup Crawler

This script demonstrates how to integrate the Beautiful Soup crawler
with the existing crypto news pipeline.
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path so we can import from crypto_news_agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from the custom BS crawler
from bs_crawler import scrape_article, scrape_and_save_articles, save_scrape_results

# Try importing from the existing pipeline
try:
    from crypto_news_agent_version_1.modules.data_collection.scraper import save_article_as_markdown
    pipeline_available = True
except ImportError:
    print("Warning: Could not import from crypto_news_agent_version_1 pipeline.")
    print("Running in standalone mode.")
    pipeline_available = False

def get_test_articles() -> List[Dict[str, str]]:
    """Get a list of test articles to scrape."""
    return [
        {
            "url": "https://crypto.news/sir-trading-offers-attacker-100k-bounty-after-losing-entire-tvl-to-exploit/",
            "title": "SIR.trading Offers Attacker Bounty"
        },
        {
            "url": "https://crypto.news/crypto-hacks-in-q1-soar-131-yoy-as-losses-hit-1-63b-data-shows/",
            "title": "Crypto Hacks in Q1 Soar 131% YoY"
        },
        {
            "url": "https://crypto.news/kentucky-drops-crypto-staking-lawsuit-against-coinbase/",
            "title": "Kentucky Drops Staking Lawsuit"
        }
    ]

def demo_standalone_mode():
    """Demonstrate the Beautiful Soup crawler in standalone mode."""
    print("\n=== Running Beautiful Soup Crawler in Standalone Mode ===\n")
    
    # Get test articles
    articles = get_test_articles()
    
    # Scrape articles and save as markdown
    results = scrape_and_save_articles(articles)
    
    # Save the results to a JSON file
    output_file = save_scrape_results(results)
    
    # Print summary
    success_count = sum(1 for r in results if r.get("success", False))
    print(f"\nSummary: Successfully scraped {success_count}/{len(articles)} articles")
    print(f"Results saved to: {output_file}")

def scrape_with_beautiful_soup(url: str) -> Optional[Dict[str, Any]]:
    """
    Scrape a URL using the Beautiful Soup crawler.
    This function can be used as a drop-in replacement for the Firecrawl scraper.
    
    Args:
        url: The URL to scrape
        
    Returns:
        Dictionary with scraped content or None if scraping failed
    """
    print(f"Scraping {url} with Beautiful Soup crawler...")
    result = scrape_article(url)
    
    if not result:
        return None
    
    # Format the result to match the expected structure of the pipeline
    return {
        "url": url,
        "title": result["metadata"].get("title", ""),
        "date": result["metadata"].get("date", ""),
        "author": result["metadata"].get("author", ""),
        "description": result["metadata"].get("description", ""),
        "content": result.get("content", ""),
        "markdown": result.get("markdown", ""),
        "image": result["metadata"].get("image", ""),
        "source": result["metadata"].get("source", ""),
        "scraped_at": result["metadata"].get("scraped_at", datetime.now().isoformat())
    }

def demo_pipeline_integration():
    """Demonstrate how to integrate with the existing pipeline."""
    if not pipeline_available:
        print("Pipeline integration not available. Run in standalone mode instead.")
        return
    
    print("\n=== Demonstrating Pipeline Integration ===\n")
    
    # Get test articles
    articles = get_test_articles()
    
    # Process each article using the Beautiful Soup crawler
    # but integrate with the existing pipeline's markdown save function
    for article in articles:
        url = article["url"]
        print(f"Processing: {url}")
        
        # Scrape with Beautiful Soup
        result = scrape_with_beautiful_soup(url)
        
        if result:
            # Save using the pipeline's markdown function
            try:
                markdown_path = save_article_as_markdown(result)
                print(f"✅ Saved to: {markdown_path}")
            except Exception as e:
                print(f"❌ Error saving markdown: {e}")
        else:
            print(f"❌ Failed to scrape: {url}")

def create_integration_example():
    """Create example code for integrating the Beautiful Soup crawler with the existing pipeline."""
    code = '''
# Example code for integrating Beautiful Soup crawler with existing pipeline

from try_new_scrawl.bs_crawler import scrape_article

def scrape_with_beautiful_soup(url: str):
    """Scrape a URL using the Beautiful Soup crawler."""
    return scrape_article(url)

# Example of modifying the existing scraper.py to use Beautiful Soup as an alternative
def scrape_url(url: str):
    """Scrape a URL using available scrapers."""
    # Try Firecrawl first if available
    if FIRECRAWL_AVAILABLE and FIRECRAWL_API_KEY:
        try:
            print(f"Using Firecrawl for {url}")
            scraped = scrape_url_with_firecrawl(url)
            
            # Check if Firecrawl succeeded
            if not scraped.get("error"):
                return scraped
                
            print(f"Firecrawl failed, trying Beautiful Soup: {scraped.get('error')}")
        except Exception as e:
            print(f"Firecrawl error: {str(e)}")
    
    # Try Beautiful Soup crawler
    try:
        print(f"Using Beautiful Soup for {url}")
        # Import the Beautiful Soup crawler
        from try_new_scrawl.bs_crawler import scrape_article
        
        # Scrape with Beautiful Soup
        result = scrape_article(url)
        
        if result:
            # Format the result to match the expected structure
            return {
                "url": url,
                "title": result["metadata"].get("title", ""),
                "date": result["metadata"].get("date", ""),
                "author": result["metadata"].get("author", ""),
                "description": result["metadata"].get("description", ""),
                "content": result.get("content", ""),
                "markdown": result.get("markdown", ""),
                "image": result["metadata"].get("image", ""),
                "source": result["metadata"].get("source", "")
            }
            
        print(f"Beautiful Soup failed, trying requests fallback")
    except Exception as e:
        print(f"Beautiful Soup error: {str(e)}")
    
    # Fallback to requests if both Firecrawl and Beautiful Soup failed
    return scrape_url_with_requests(url)
'''
    
    # Save the example code to a file
    with open("integration_example.py", "w") as f:
        f.write(code)
    
    print("\nCreated integration example code in integration_example.py")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Integrate Beautiful Soup crawler with the existing pipeline")
    parser.add_argument("--mode", choices=["standalone", "pipeline", "example"], 
                        default="standalone", help="Mode to run")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("BEAUTIFUL SOUP CRAWLER INTEGRATION")
    print("=" * 60)
    
    if args.mode == "standalone":
        demo_standalone_mode()
    elif args.mode == "pipeline":
        demo_pipeline_integration()
    elif args.mode == "example":
        create_integration_example()
    
    print("\nIntegration demonstration completed!")

if __name__ == "__main__":
    main() 