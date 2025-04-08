"""
Custom Crawler Controller

This module controls the execution of custom crawlers for various crypto news websites.
"""

import os
import sys
import json
import time
import random
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
import shutil

# Define paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../../"))

# Add paths to crawlers
CRAWLER_PATHS = {
    "beincrypto": os.path.join(PROJECT_ROOT, "beincrypto.com"),
    "bitcoin": os.path.join(PROJECT_ROOT, "bitcoin.com"),
    "coindesk": os.path.join(PROJECT_ROOT, "coindesk.com"),
    "cointelegraph": os.path.join(PROJECT_ROOT, "cointelegraph.com"),
    "cryptonews": os.path.join(PROJECT_ROOT, "cryptonews.com"),
    "utoday": os.path.join(PROJECT_ROOT, "u.today")
}

# Shell scripts to run each crawler
CRAWLER_SCRIPTS = {
    "beincrypto": "run_beincrypto.sh",
    "bitcoin": "run_bitcoincom_selenium.sh",
    "coindesk": "run_crawler.sh",
    "cointelegraph": "run_cointelegraph.sh",
    "cryptonews": "run_cryptonews.sh",
    "utoday": "run_utoday.sh"
}

def run_crawler(crawler_name: str, max_articles: int = 10, output_dir: str = None) -> bool:
    """
    Run a specific crawler.
    
    Args:
        crawler_name: Name of the crawler to run
        max_articles: Maximum number of articles to fetch
        output_dir: Output directory for scraped data
        
    Returns:
        True if successful, False otherwise
    """
    if crawler_name not in CRAWLER_PATHS:
        print(f"Error: Crawler '{crawler_name}' not found.")
        return False
    
    crawler_path = CRAWLER_PATHS[crawler_name]
    if not os.path.exists(crawler_path):
        print(f"Error: Crawler directory '{crawler_path}' does not exist.")
        return False
    
    script_name = CRAWLER_SCRIPTS.get(crawler_name)
    if not script_name:
        print(f"Error: No script defined for crawler '{crawler_name}'.")
        return False
    
    script_path = os.path.join(crawler_path, script_name)
    if not os.path.exists(script_path):
        print(f"Error: Script '{script_path}' does not exist.")
        return False
    
    # Make script executable if it's not already
    os.chmod(script_path, 0o755)
    
    # Build command
    cmd = [script_path]
    
    # Add options
    if max_articles:
        cmd.extend(["-a", str(max_articles)])
    
    if output_dir:
        cmd.extend(["-o", output_dir])
    
    try:
        # Change to crawler directory
        original_dir = os.getcwd()
        os.chdir(crawler_path)
        
        print(f"Running crawler: {crawler_name}")
        print(f"Command: {' '.join(cmd)}")
        
        # Run crawler
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor output
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"[{crawler_name}] {output.strip()}")
        
        # Get return code
        return_code = process.poll()
        
        # Change back to original directory
        os.chdir(original_dir)
        
        if return_code == 0:
            print(f"Crawler '{crawler_name}' completed successfully.")
            return True
        else:
            print(f"Crawler '{crawler_name}' failed with return code {return_code}.")
            return False
    
    except Exception as e:
        print(f"Error running crawler '{crawler_name}': {e}")
        # Ensure we change back to original directory
        if 'original_dir' in locals():
            os.chdir(original_dir)
        return False

def find_latest_data_directory(crawler_name: str) -> Optional[str]:
    """
    Find the latest data directory for a specific crawler.
    
    Args:
        crawler_name: Name of the crawler
        
    Returns:
        Path to the latest data directory or None if not found
    """
    crawler_path = CRAWLER_PATHS.get(crawler_name)
    if not crawler_path:
        return None
    
    data_dir = os.path.join(crawler_path, "scraped_data")
    if not os.path.exists(data_dir):
        return None
    
    # Get all subdirectories
    subdirs = [os.path.join(data_dir, d) for d in os.listdir(data_dir) 
               if os.path.isdir(os.path.join(data_dir, d))]
    
    if not subdirs:
        return None
    
    # Sort by modification time (newest first)
    latest_dir = max(subdirs, key=os.path.getmtime)
    
    return latest_dir

def collect_scraped_data(crawler_names: List[str], output_dir: str = "data/scraped_articles", extension: str = ".md") -> List[Dict[str, Any]]:
    """
    Collect scraped data from all specified crawlers.
    
    Args:
        crawler_names: List of crawler names to collect data from
        output_dir: Directory to copy the files to
        extension: File extension to collect (default: .md)
        
    Returns:
        List of article data with metadata
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    collected_articles = []
    
    for crawler_name in crawler_names:
        latest_dir = find_latest_data_directory(crawler_name)
        if not latest_dir:
            print(f"No data directory found for crawler '{crawler_name}'.")
            continue
        
        print(f"Collecting data from {crawler_name}: {latest_dir}")
        
        # Find all files with the specified extension
        files = [f for f in os.listdir(latest_dir) if f.endswith(extension)]
        
        for file_name in files:
            file_path = os.path.join(latest_dir, file_name)
            
            # Read file content
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Extract metadata from file name or content
                title = ""
                date = ""
                
                # Try to extract title from markdown
                if extension == ".md":
                    title_match = content.split("\n")[0].strip()
                    if title_match.startswith("# "):
                        title = title_match[2:]
                
                # If no title found in content, try to extract from filename
                if not title:
                    # Typical filename format: YYYYMMDD_HHMMSS_title.md
                    parts = file_name.split("_", 2)
                    if len(parts) > 2:
                        # Extract date part
                        date_part = parts[0] + "_" + parts[1]
                        try:
                            date_obj = datetime.strptime(date_part, "%Y%m%d_%H%M%S")
                            date = date_obj.strftime("%Y-%m-%d")
                        except ValueError:
                            date = ""
                        
                        # Extract title part
                        title_part = parts[2].rsplit(".", 1)[0]  # Remove extension
                        title = title_part.replace("_", " ").title()
                
                # Create destination filename
                dest_filename = f"{crawler_name}_{file_name}"
                dest_path = os.path.join(output_dir, dest_filename)
                
                # Copy file to output directory
                shutil.copy2(file_path, dest_path)
                
                # Add article to list
                article_data = {
                    "title": title,
                    "date": date,
                    "content": content,
                    "source": crawler_name,
                    "file_path": dest_path,
                    "url": f"file://{os.path.abspath(dest_path)}"
                }
                
                collected_articles.append(article_data)
                
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
    
    print(f"Collected {len(collected_articles)} articles from {len(crawler_names)} crawlers.")
    
    return collected_articles

def run_all_crawlers(crawler_names: List[str] = None, max_articles: int = 10) -> Dict[str, bool]:
    """
    Run all available crawlers or a subset of them.
    
    Args:
        crawler_names: List of crawler names to run (if None, runs all available crawlers)
        max_articles: Maximum number of articles to fetch per crawler
        
    Returns:
        Dictionary with crawler names as keys and success status as values
    """
    if crawler_names is None:
        # Use all available crawlers
        from . import AVAILABLE_CRAWLERS
        crawler_names = AVAILABLE_CRAWLERS
    
    results = {}
    
    for crawler_name in crawler_names:
        print(f"\n{'='*50}")
        print(f"Running crawler: {crawler_name}")
        print(f"{'='*50}\n")
        
        success = run_crawler(crawler_name, max_articles)
        results[crawler_name] = success
        
        # Add a delay between crawlers to avoid overwhelming system resources
        if crawler_name != crawler_names[-1]:
            delay = random.uniform(3, 5)
            print(f"Waiting {delay:.2f} seconds before starting next crawler...")
            time.sleep(delay)
    
    # Print summary
    print("\n\n" + "="*50)
    print("Crawler Execution Summary:")
    print("="*50)
    
    for crawler, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        print(f"{crawler:15}: {status}")
    
    print("="*50)
    
    return results 