#!/usr/bin/env python3
"""
Test script for CoinDesk crawler components
"""

import os
import sys
import time
import argparse
from urllib.parse import urljoin

# Import from crawler module
try:
    from coindesk_crawler import (
        setup_selenium_driver,
        get_page_links,
        scrape_article,
        COINDESK_CONFIG,
        make_request,
        SELENIUM_AVAILABLE
    )
except ImportError:
    print("Error: Cannot import from coindesk_crawler.py")
    print("Make sure the file is in the current directory")
    sys.exit(1)

def test_selenium():
    """Test Selenium WebDriver setup"""
    print("\n==== Testing Selenium WebDriver ====")
    
    if not SELENIUM_AVAILABLE:
        print("✗ Selenium is not available")
        print("  Install with: pip install selenium webdriver-manager")
        return False
    
    try:
        driver = setup_selenium_driver()
        if not driver:
            print("✗ Failed to initialize Selenium WebDriver")
            return False
        
        print("✓ Selenium WebDriver initialized successfully")
        
        # Try loading a simple page
        print("Testing page load with Selenium...")
        driver.get("https://www.google.com")
        time.sleep(2)
        title = driver.title
        
        print(f"✓ Loaded page with title: {title}")
        
        # Clean up
        driver.quit()
        return True
    except Exception as e:
        print(f"✗ Selenium test failed: {e}")
        return False

def test_link_extraction():
    """Test link extraction from CoinDesk pages"""
    print("\n==== Testing Link Extraction ====")
    
    try:
        # Use the homepage
        url = COINDESK_CONFIG["base_url"]
        print(f"Extracting links from {url}...")
        
        links = get_page_links(url)
        
        article_links = [url for url, link_type in links if link_type == "article"]
        section_links = [url for url, link_type in links if link_type == "section"]
        
        print(f"Found {len(article_links)} article links and {len(section_links)} section links")
        
        if not article_links and not section_links:
            print("✗ No links found - extraction might be failing")
            return False
        
        print("✓ Link extraction successful")
        
        # Print a few examples
        if article_links:
            print("\nSample article links:")
            for i, url in enumerate(article_links[:3]):
                print(f"  {i+1}. {url}")
        
        if section_links:
            print("\nSample section links:")
            for i, url in enumerate(section_links[:3]):
                print(f"  {i+1}. {url}")
        
        return True
    except Exception as e:
        print(f"✗ Link extraction test failed: {e}")
        return False

def test_article_scraping():
    """Test article scraping functionality"""
    print("\n==== Testing Article Scraping ====")
    
    try:
        # Create a temporary directory for test output
        temp_dir = "_test_articles"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Try with a known article URL or get one from the homepage
        test_article = None
        print("Finding an article to test scraping...")
        
        homepage_links = get_page_links(COINDESK_CONFIG["base_url"])
        article_links = [url for url, link_type in homepage_links if link_type == "article"]
        
        if article_links:
            test_article = article_links[0]
        
        if not test_article:
            # Fallback to a specific section like markets
            markets_url = urljoin(COINDESK_CONFIG["base_url"], "/markets")
            section_links = get_page_links(markets_url)
            article_links = [url for url, link_type in section_links if link_type == "article"]
            
            if article_links:
                test_article = article_links[0]
        
        if not test_article:
            print("✗ Could not find an article to test scraping")
            return False
        
        print(f"Testing article scraping with: {test_article}")
        result = scrape_article(test_article, temp_dir)
        
        if not result.get("success", False):
            print(f"✗ Article scraping failed: {result.get('error', 'Unknown error')}")
            return False
        
        print(f"✓ Article scraped successfully: {result.get('title')}")
        print(f"  Saved to: {result.get('output_file')}")
        
        # Check if file exists
        if os.path.isfile(result.get('output_file')):
            filesize = os.path.getsize(result.get('output_file'))
            print(f"  File size: {filesize} bytes")
            
            if filesize < 100:
                print("✗ Warning: Output file is very small, content might be incomplete")
        else:
            print("✗ Output file does not exist")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Article scraping test failed: {e}")
        return False
    finally:
        # Clean up temp files if needed
        # Uncomment if you want to remove the test files
        # import shutil
        # if os.path.exists(temp_dir):
        #     shutil.rmtree(temp_dir)
        pass

def main():
    parser = argparse.ArgumentParser(description="Test CoinDesk Crawler Components")
    parser.add_argument("--selenium-only", action="store_true", help="Test Selenium setup only")
    parser.add_argument("--links-only", action="store_true", help="Test link extraction only")
    parser.add_argument("--article-only", action="store_true", help="Test article scraping only")
    
    args = parser.parse_args()
    
    # Track test results
    results = []
    
    # Run tests based on arguments
    if args.selenium_only:
        results.append(("Selenium", test_selenium()))
    elif args.links_only:
        results.append(("Link Extraction", test_link_extraction()))
    elif args.article_only:
        results.append(("Article Scraping", test_article_scraping()))
    else:
        # Run all tests
        results.append(("Selenium", test_selenium()))
        results.append(("Link Extraction", test_link_extraction()))
        results.append(("Article Scraping", test_article_scraping()))
    
    # Print summary
    print("\n==== Test Summary ====")
    all_passed = True
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        if not result:
            all_passed = False
        print(f"{test_name}: {status}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main()) 