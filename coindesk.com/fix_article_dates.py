#!/usr/bin/env python3
"""
Fix Article Dates

This script corrects the publication dates in extracted article files
by extracting them from the article URLs.
"""

import os
import re
import json
import glob
import argparse
from datetime import datetime

def extract_date_from_url(url):
    """
    Extract publication date from CoinDesk article URL.
    CoinDesk URLs typically include the date in the format: /YYYY/MM/DD/
    """
    # Match YYYY/MM/DD pattern in URL
    date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if date_match:
        year, month, day = date_match.groups()
        return f"{year}-{month}-{day}"
    return None

def fix_article_dates(directory, output_dir=None):
    """
    Fix article dates in all JSON files in the specified directory.
    
    Args:
        directory: Directory containing JSON files with article data
        output_dir: Directory to save fixed files (if None, overwrite original)
    """
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Find all JSON files in the directory
    json_files = glob.glob(os.path.join(directory, "*.json"))
    
    if not json_files:
        print(f"No JSON files found in {directory}")
        return
    
    print(f"Found {len(json_files)} JSON files in {directory}")
    
    # Track statistics
    fixed_count = 0
    total_articles = 0
    
    # Process each JSON file
    for json_file in json_files:
        filename = os.path.basename(json_file)
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if this is an article collection
            if "articles" in data:
                articles = data["articles"]
                total_articles += len(articles)
                
                # Process each article
                for article in articles:
                    # Try to extract date from URL
                    if "source" in article and article["source"]:
                        extracted_date = extract_date_from_url(article["source"])
                        
                        # If current date is suspicious (video timestamp) and we found a date in URL
                        if (article.get("date", "").startswith("0 seconds") or 
                            "seconds" in article.get("date", "")) and extracted_date:
                            article["date"] = extracted_date
                            fixed_count += 1
                
                # Save the updated data
                output_file = os.path.join(output_dir, filename) if output_dir else json_file
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                
                print(f"Processed {filename}: Fixed {fixed_count} dates out of {len(articles)} articles")
            
            # Handle individual article files
            elif "filename" in data and "source" in data:
                total_articles += 1
                # Try to extract date from URL
                if data.get("source"):
                    extracted_date = extract_date_from_url(data["source"])
                    
                    # If current date is suspicious (video timestamp) and we found a date in URL
                    if (data.get("date", "").startswith("0 seconds") or 
                        "seconds" in data.get("date", "")) and extracted_date:
                        data["date"] = extracted_date
                        fixed_count += 1
                
                # Save the updated data
                output_file = os.path.join(output_dir, filename) if output_dir else json_file
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                
                print(f"Processed {filename}: Fixed date for individual article")
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    print(f"\nSummary:")
    print(f"Total articles: {total_articles}")
    print(f"Fixed dates: {fixed_count}")
    print(f"Percentage fixed: {fixed_count/total_articles*100:.1f}%")

def fix_text_files(directory, output_dir=None):
    """
    Fix dates in text files (clean article versions)
    
    Args:
        directory: Directory containing text files with article content
        output_dir: Directory to save fixed files (if None, overwrite original)
    """
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Find all text files in the directory
    text_files = glob.glob(os.path.join(directory, "*.txt"))
    
    if not text_files:
        print(f"No text files found in {directory}")
        return
    
    print(f"Found {len(text_files)} text files in {directory}")
    
    # Track statistics
    fixed_count = 0
    
    # Process each text file
    for text_file in text_files:
        filename = os.path.basename(text_file)
        
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract source URL
            source_match = re.search(r'^Source: (.+)$', content, re.MULTILINE)
            if source_match:
                source_url = source_match.group(1)
                extracted_date = extract_date_from_url(source_url)
                
                # If we found a date and need to replace the current date
                if extracted_date:
                    # Replace the date line - make sure to include "Date: " prefix
                    updated_content = re.sub(
                        r'^Date: .+$', 
                        f'Date: {extracted_date}', 
                        content, 
                        flags=re.MULTILINE
                    )
                    
                    if updated_content != content:
                        fixed_count += 1
                        
                        # Save the updated content
                        output_file = os.path.join(output_dir, filename) if output_dir else text_file
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(updated_content)
                        
                        print(f"Fixed date in {filename}")
                    else:
                        print(f"No changes needed for {filename}")
        
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    print(f"\nSummary:")
    print(f"Total text files: {len(text_files)}")
    print(f"Fixed dates: {fixed_count}")
    print(f"Percentage fixed: {fixed_count/len(text_files)*100:.1f}%")

def main():
    parser = argparse.ArgumentParser(description="Fix article dates in extracted files")
    parser.add_argument("--json-dir", help="Directory containing JSON files with article data")
    parser.add_argument("--text-dir", help="Directory containing text files with article content")
    parser.add_argument("--output-dir", help="Directory to save fixed files (if omitted, will overwrite original)")
    
    args = parser.parse_args()
    
    if not args.json_dir and not args.text_dir:
        parser.error("At least one of --json-dir or --text-dir is required")
    
    if args.json_dir:
        fix_article_dates(args.json_dir, args.output_dir)
    
    if args.text_dir:
        fix_text_files(args.text_dir, args.output_dir)

if __name__ == "__main__":
    main() 