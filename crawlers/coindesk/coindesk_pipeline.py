#!/usr/bin/env python3
"""
CoinDesk Pipeline

A complete pipeline that:
1. Crawls articles from CoinDesk
2. Cleans the articles
3. Extracts structured data
4. Fixes article dates
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime

def run_command(command, description):
    """Run a command and print its output in real-time"""
    print(f"\n{'='*50}")
    print(f"STEP: {description}")
    print(f"{'='*50}")
    print(f"Running: {' '.join(command)}")
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Print output in real-time
    for line in process.stdout:
        print(line, end='')
    
    # Wait for process to complete and get return code
    return_code = process.wait()
    
    if return_code != 0:
        print(f"\nERROR: Command failed with exit code {return_code}")
        return False
    
    print(f"\nSUCCESS: {description} completed")
    return True

def main():
    parser = argparse.ArgumentParser(description="CoinDesk Complete Pipeline")
    parser.add_argument("--max-articles", type=int, default=10,
                        help="Maximum number of articles to scrape")
    parser.add_argument("--max-sections", type=int, default=5,
                        help="Maximum number of section pages to visit")
    parser.add_argument("--base-dir", default="pipeline_output",
                        help="Base directory for all outputs")
    
    args = parser.parse_args()
    
    # Create timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Setup directories
    base_dir = args.base_dir
    scraped_dir = os.path.join(base_dir, "scraped_data")
    clean_dir = os.path.join(base_dir, "clean_articles")
    extracted_dir = os.path.join(base_dir, "extracted_data")
    
    # Create directories
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(scraped_dir, exist_ok=True)
    os.makedirs(clean_dir, exist_ok=True)
    os.makedirs(extracted_dir, exist_ok=True)
    
    print(f"Pipeline output will be stored in: {base_dir}")
    
    # Step 1: Crawl articles
    success = run_command(
        [
            "python", "coindesk_crawler.py",
            "--max-articles", str(args.max_articles),
            "--max-sections", str(args.max_sections),
            "--output-dir", scraped_dir
        ],
        "Crawling articles from CoinDesk"
    )
    
    if not success:
        print("Pipeline failed at the crawling step")
        return 1
    
    # Find the most recent crawl output directory
    crawl_dirs = [d for d in os.listdir(scraped_dir) if d.startswith("coindesk_")]
    if not crawl_dirs:
        print("No crawled data found")
        return 1
    
    crawl_dirs.sort(reverse=True)  # Sort in reverse to get latest first
    latest_crawl_dir = os.path.join(scraped_dir, crawl_dirs[0])
    print(f"Using latest crawl data from: {latest_crawl_dir}")
    
    # Step 2: Clean articles
    success = run_command(
        [
            "python", "clean_article_content.py",
            latest_crawl_dir,
            "--format", "text",
            "--output-dir", clean_dir
        ],
        "Cleaning article content"
    )
    
    if not success:
        print("Pipeline failed at the cleaning step")
        return 1
    
    # Step 3: Fix dates in cleaned articles
    success = run_command(
        [
            "python", "fix_article_dates.py",
            "--text-dir", clean_dir
        ],
        "Fixing article dates"
    )
    
    if not success:
        print("Pipeline failed at the date fixing step")
        return 1
    
    # Step 4: Extract article data
    success = run_command(
        [
            "python", "extract_article_data.py",
            latest_crawl_dir,
            "--format", "json",
            "--output", os.path.join(extracted_dir, f"articles_{timestamp}.json")
        ],
        "Extracting article data"
    )
    
    if not success:
        print("Pipeline failed at the extraction step")
        return 1
    
    print("\n" + "="*50)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("="*50)
    print(f"Outputs saved in: {base_dir}")
    print(f"- Scraped articles: {latest_crawl_dir}")
    print(f"- Cleaned articles: {clean_dir}")
    print(f"- Extracted data: {extracted_dir}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 