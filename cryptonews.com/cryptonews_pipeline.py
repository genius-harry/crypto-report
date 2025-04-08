#!/usr/bin/env python3
"""
Cryptonews Complete Pipeline

This script provides a complete pipeline for crawling, processing, and cleaning
cryptonews.com articles. It handles:
1. Crawling articles using undetected-chromedriver to bypass Cloudflare
2. Cleaning and processing the raw content
3. Saving the results in a structured format
"""

import os
import sys
import argparse
import subprocess
import json
from datetime import datetime
from pathlib import Path
import time

def setup_environment():
    """Set up the environment, installing dependencies if needed."""
    try:
        # Check if required packages are installed
        import undetected_chromedriver
        import selenium
        import bs4
        import html2text
    except ImportError:
        print("Installing required packages...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "undetected-chromedriver", "selenium", "beautifulsoup4", "html2text"
        ])
        
    print("Environment setup complete.")

def run_crawler(max_articles, max_sections, output_dir, headless=True):
    """
    Run the cryptonews crawler.
    
    Args:
        max_articles: Maximum number of articles to crawl per section
        max_sections: Maximum number of sections to crawl
        output_dir: Directory to save output
        headless: Whether to run in headless mode
        
    Returns:
        Path to the scraped data directory
    """
    from cryptonews_crawler import CryptonewsCrawler
    
    print(f"\n{'='*80}\nStarting Cryptonews Crawler\n{'='*80}")
    
    crawler = CryptonewsCrawler(
        output_dir=output_dir,
        max_articles=max_articles,
        max_sections=max_sections,
        headless=headless
    )
    
    # Run the crawler
    crawler.crawl()
    
    # Return the path to the most recent crawl
    crawl_dirs = sorted(Path(output_dir).glob("*"), key=os.path.getmtime, reverse=True)
    if crawl_dirs:
        return str(crawl_dirs[0])
    return output_dir

def run_cleaner(input_dir, output_dir):
    """
    Run the article cleaner on scraped content.
    
    Args:
        input_dir: Directory containing scraped markdown files
        output_dir: Directory to save cleaned articles
        
    Returns:
        Number of articles processed
    """
    from clean_article_content import process_directory
    
    print(f"\n{'='*80}\nStarting Article Cleaner\n{'='*80}")
    
    results = process_directory(input_dir, output_dir)
    return len(results)

def generate_pipeline_summary(crawl_dir, clean_dir, start_time):
    """
    Generate a summary of the pipeline run.
    
    Args:
        crawl_dir: Directory containing crawled data
        clean_dir: Directory containing cleaned data
        start_time: Start time of the pipeline
        
    Returns:
        Dictionary with pipeline summary
    """
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Load crawl summary
    crawl_summary_path = os.path.join(crawl_dir, "summary.json")
    crawl_data = {}
    if os.path.exists(crawl_summary_path):
        with open(crawl_summary_path, "r", encoding="utf-8") as f:
            try:
                crawl_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse crawl summary file: {crawl_summary_path}")
    
    # Load clean summary
    clean_summary_path = os.path.join(clean_dir, "summary.json")
    clean_data = {}
    if os.path.exists(clean_summary_path):
        with open(clean_summary_path, "r", encoding="utf-8") as f:
            try:
                clean_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse clean summary file: {clean_summary_path}")
    
    # Create pipeline summary
    summary = {
        "pipeline_start_time": start_time.isoformat(),
        "pipeline_end_time": end_time.isoformat(),
        "pipeline_duration_seconds": duration,
        "crawl_directory": crawl_dir,
        "clean_directory": clean_dir,
        "articles_crawled": crawl_data.get("articles_scraped", 0),
        "successful_crawls": crawl_data.get("successful_scrapes", 0),
        "articles_cleaned": clean_data.get("files_processed", 0)
    }
    
    # Save pipeline summary
    summary_path = os.path.join(clean_dir, "pipeline_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    
    return summary

def run_pipeline(args):
    """
    Run the complete pipeline.
    
    Args:
        args: Command-line arguments
    """
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    
    # Create directory structure
    pipeline_dir = os.path.join("pipeline_output")
    os.makedirs(pipeline_dir, exist_ok=True)
    
    # Define directories
    scraped_dir = os.path.join(pipeline_dir, "scraped_data")
    cleaned_dir = os.path.join(pipeline_dir, "clean_articles")
    
    # Make sure directories exist
    os.makedirs(scraped_dir, exist_ok=True)
    os.makedirs(cleaned_dir, exist_ok=True)
    
    # Setup environment
    setup_environment()
    
    try:
        # Step 1: Run the crawler
        crawl_output = run_crawler(
            max_articles=args.max_articles,
            max_sections=args.max_sections,
            output_dir=scraped_dir,
            headless=not args.visible
        )
        
        # Step 2: Process and clean the articles
        run_cleaner(
            input_dir=crawl_output,
            output_dir=cleaned_dir
        )
        
        # Step 3: Generate pipeline summary
        summary = generate_pipeline_summary(
            crawl_dir=crawl_output,
            clean_dir=cleaned_dir,
            start_time=start_time
        )
        
        # Print summary
        print(f"\n{'='*80}\nPipeline Complete\n{'='*80}")
        print(f"Pipeline duration: {summary['pipeline_duration_seconds']:.2f} seconds")
        print(f"Articles crawled: {summary['articles_crawled']}")
        print(f"Successful crawls: {summary['successful_crawls']}")
        print(f"Articles cleaned: {summary['articles_cleaned']}")
        print(f"Cleaned articles directory: {cleaned_dir}")
        
    except Exception as e:
        print(f"Error in pipeline: {e}")
        sys.exit(1)

def main():
    """Parse command-line arguments and run the pipeline."""
    parser = argparse.ArgumentParser(description="Cryptonews Complete Pipeline")
    parser.add_argument("--max-articles", type=int, default=3, 
                        help="Maximum number of articles to crawl per section")
    parser.add_argument("--max-sections", type=int, default=2,
                        help="Maximum number of sections to crawl")
    parser.add_argument("--visible", action="store_true",
                        help="Run Chrome in visible mode (not headless)")
    
    args = parser.parse_args()
    run_pipeline(args)

if __name__ == "__main__":
    main() 