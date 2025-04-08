#!/usr/bin/env python3
"""
Test script for the custom Beautiful Soup crawler.
This script tests the crawler with a sample URL.
"""

import os
import json
from bs_crawler import scrape_article, scrape_and_save_articles

def test_single_url():
    """Test scraping a single URL."""
    # Current crypto news URL provided by the user
    url = "https://crypto.news/tether-buys-another-735m-in-btc-in-q1-bringing-total-holdings-to-8-2b/"
    
    print(f"Testing BS crawler with URL: {url}")
    
    # Scrape the article
    result = scrape_article(url)
    
    if result:
        print("\nSuccessfully scraped article!")
        print(f"Title: {result['metadata'].get('title', '')}")
        print(f"Author: {result['metadata'].get('author', '')}")
        print(f"Date: {result['metadata'].get('date', '')}")
        print(f"Description: {result['metadata'].get('description', '')[:100]}...")
        
        # Save the full result to a file for inspection
        with open("bs_test_result.json", "w", encoding="utf-8") as f:
            # Use a simplified representation for HTML content to make the file readable
            safe_result = result.copy()
            if "html" in safe_result:
                safe_result["html"] = f"[HTML content - {len(result['html'])} characters]"
            
            json.dump(safe_result, f, ensure_ascii=False, indent=2)
        
        print("Full response saved to bs_test_result.json")
        
        # Print a preview of the markdown content
        markdown_preview = result.get("markdown", "")[:500]
        print("\nMarkdown content preview:")
        print("=" * 50)
        print(markdown_preview + "...")
        print("=" * 50)
    else:
        print("Failed to scrape the URL!")

def test_multiple_urls():
    """Test scraping multiple URLs."""
    # Sample list of crypto news URLs - updated to current available ones
    urls = [
        {"url": "https://crypto.news/sir-trading-offers-attacker-100k-bounty-after-losing-entire-tvl-to-exploit/"},
        {"url": "https://crypto.news/crypto-hacks-in-q1-soar-131-yoy-as-losses-hit-1-63b-data-shows/"},
        {"url": "https://crypto.news/kentucky-drops-crypto-staking-lawsuit-against-coinbase/"}
    ]
    
    print(f"Testing BS crawler with {len(urls)} URLs")
    
    # Scrape the articles and save as markdown
    results = scrape_and_save_articles(urls)
    
    # Print summary
    success_count = sum(1 for r in results if r.get("success", False))
    print(f"\nSuccessfully scraped {success_count}/{len(urls)} articles")
    
    # Print details for each result
    for i, result in enumerate(results):
        print(f"\nArticle {i+1}:")
        print(f"URL: {result.get('url', '')}")
        print(f"Title: {result.get('title', '')}")
        print(f"Success: {result.get('success', False)}")
        if result.get("success", False):
            print(f"Saved to: {result.get('markdown_file', '')}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")

def compare_with_firecrawl():
    """
    TODO: Implement a comparison between Beautiful Soup crawler and Firecrawl.
    This would:
    1. Scrape the same set of URLs with both crawlers
    2. Compare extraction quality, success rates, and performance
    3. Generate a comparison report
    """
    print("Comparison with Firecrawl not yet implemented.")
    print("This would be useful to evaluate the custom crawler against Firecrawl.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the Beautiful Soup crawler")
    parser.add_argument("--test", choices=["single", "multiple", "compare"], 
                        default="single", help="Test type to run")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("BEAUTIFUL SOUP CRAWLER TEST")
    print("=" * 50)
    
    if args.test == "single":
        test_single_url()
    elif args.test == "multiple":
        test_multiple_urls()
    elif args.test == "compare":
        compare_with_firecrawl()
    
    print("\nTest completed!") 