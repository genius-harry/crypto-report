#!/usr/bin/env python3
"""
Crypto News Crawler - Universal Entry Point

This script provides a unified interface to our different crawler implementations,
automatically selecting the appropriate crawler based on the URL.
"""

import os
import sys
import argparse
from urllib.parse import urlparse
import subprocess
import json
from datetime import datetime

# Define site-specific configurations
SITE_CONFIGS = {
    "coindesk.com": {
        "requires_javascript": True,
        "crawler": "enhanced_subpage_crawler.py",
    },
    "crypto.news": {
        "requires_javascript": False,
        "crawler": "bs_subpage_crawler.py",
    },
    # Add more site configs as needed
}

def detect_site_type(url):
    """
    Detect the site type from the URL and return appropriate crawler type.
    
    Args:
        url: URL to analyze
        
    Returns:
        Dictionary with site configuration
    """
    domain = urlparse(url).netloc.replace("www.", "")
    
    # Return site-specific config if available
    if domain in SITE_CONFIGS:
        return {
            "domain": domain,
            **SITE_CONFIGS[domain]
        }
    
    # Default configuration
    return {
        "domain": domain,
        "requires_javascript": False,
        "crawler": "bs_crawler.py" if "//" in url else "bs_subpage_crawler.py",
    }

def run_crawler(url, output_dir=None, max_articles=5, force_selenium=False):
    """
    Run the appropriate crawler for the given URL.
    
    Args:
        url: URL to crawl
        output_dir: Optional output directory
        max_articles: Maximum number of articles to scrape (for subpage crawlers)
        force_selenium: Whether to force using Selenium
        
    Returns:
        Exit code from the crawler process
    """
    site_config = detect_site_type(url)
    
    # Define the command to run
    cmd = ["python"]
    
    # Select the appropriate crawler
    if site_config["requires_javascript"] or force_selenium:
        # For sites requiring JavaScript
        if "//" in url and not url.endswith("/"):
            # Single article with JavaScript
            cmd.extend(["selenium_crawler.py", url])
            
            # Add output path if specified
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_article.md"
                output_path = os.path.join(output_dir, filename)
                cmd.extend(["--output", output_path])
        else:
            # Multiple articles with JavaScript
            cmd.extend(["enhanced_subpage_crawler.py", url, "--max", str(max_articles)])
            if force_selenium:
                cmd.append("--force-selenium")
                
            # Add output directory for enhanced crawler
            if output_dir:
                cmd.extend(["--output-dir", output_dir])
    else:
        # For sites not requiring JavaScript
        if "//" in url and not url.endswith("/"):
            # Single article
            cmd.extend(["bs_crawler.py", url])
            
            # Add output path if specified
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_article.md"
                output_path = os.path.join(output_dir, filename)
                cmd.extend(["--output", output_path])
        else:
            # Multiple articles with BS4
            cmd.extend(["bs_subpage_crawler.py", url, "--max", str(max_articles)])
            
            # BS subpage crawler uses --output parameter, not --output-dir
            if output_dir:
                cmd.extend(["--output", output_dir])
    
    # Print the command being run
    print(f"Running: {' '.join(cmd)}")
    
    # Run the selected crawler
    try:
        return subprocess.run(cmd, check=True).returncode
    except subprocess.CalledProcessError as e:
        print(f"Error running crawler: {e}")
        return e.returncode

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Unified crypto news crawler")
    parser.add_argument("--url", help="URL of the article or site to crawl")
    parser.add_argument("--max", type=int, default=5, help="Maximum number of articles to scrape")
    parser.add_argument("--output-dir", help="Custom output directory")
    parser.add_argument("--force-selenium", action="store_true", help="Force using Selenium for JavaScript rendering")
    parser.add_argument("--list-sites", action="store_true", help="List supported sites and their configurations")
    
    args = parser.parse_args()
    
    # List supported sites if requested
    if args.list_sites:
        print("Supported sites:")
        for domain, config in SITE_CONFIGS.items():
            js_status = "Requires JavaScript" if config["requires_javascript"] else "Standard HTML"
            crawler = config["crawler"]
            print(f"  - {domain}: {js_status} (uses {crawler})")
        return 0
    
    # Require URL for crawling
    if not args.url:
        parser.error("URL is required unless using --list-sites")
    
    # Run the appropriate crawler
    return run_crawler(
        args.url, 
        output_dir=args.output_dir, 
        max_articles=args.max,
        force_selenium=args.force_selenium
    )

if __name__ == "__main__":
    sys.exit(main()) 