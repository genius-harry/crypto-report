#!/usr/bin/env python3
"""
Clean Article Content

This script extracts title, author, and cleans the article content from markdown files,
removing navigation elements, ads, and other non-essential content.
"""

import os
import json
import re
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

def clean_content(content: str) -> str:
    """
    Clean up the content by removing navigation elements, ads, etc.
    
    Args:
        content: The raw article content
        
    Returns:
        Cleaned content
    """
    # Remove cryptocurrency price ticker section
    content = re.sub(r'\[BTC\$.*?\]\(/price/.*?\)(\s*\[.*?\]\(/price/.*?\))*\s*', '', content)
    
    # Remove navigation elements
    content = re.sub(r'\n\s*\* \[.*?\]\(.*?\)\s*', '', content)
    
    # Remove Ad section
    content = re.sub(r'Ad\n\n.*?Logo.*?\n\n', '', content)
    
    # Remove Share button
    content = re.sub(r'Share\n\n', '', content)
    
    # Remove video player sections completely
    content = re.sub(r'Tristan Thompson.*?Story continues', '', content, flags=re.DOTALL)
    content = re.sub(r'00:05\s*18:58\s*19:03\s*', '', content)
    content = re.sub(r'Press shift question mark.*?Seek %0-9', '', content, flags=re.DOTALL)
    
    # Remove newsletter signup
    content = re.sub(r"Don't miss another story.*?privacy policy.*?\)\.\n\n", '', content)
    
    # Remove footer sections
    content = re.sub(r'\* \* \*\n\nAbout.*', '', content, flags=re.DOTALL)
    content = re.sub(r'\[\]\(/ "CoinDesk homepage"\).*', '', content, flags=re.DOTALL)
    
    # Remove weird characters at the end of the file
    content = re.sub(r'\n\[%[^\n]*$', '', content)
    
    # Remove tags section
    content = re.sub(r'\[.*?\]\(/tag/.*?\)(\s*\[.*?\]\(/tag/.*?\))*\s*', '', content)
    
    # Remove author bio section
    content = re.sub(r'#+ \[.*?\]\(/author/.*?\).*?Email"\)', '', content, flags=re.DOTALL)
    
    # Remove image links with minimal text
    content = re.sub(r'!\[.*?\]\(/_next/image.*?\)\n\n', '', content)
    
    # Clean up multiple newlines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()

def extract_and_clean_article(file_path: str) -> Dict[str, Any]:
    """
    Extract title, author, and clean content from a markdown file.
    
    Args:
        file_path: Path to the markdown file
        
    Returns:
        Dictionary with extracted and cleaned data
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract title (first line starting with #)
    title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else "Unknown Title"
    
    # Extract author
    author_match = re.search(r'^Author: (.+)$', content, re.MULTILINE)
    author = author_match.group(1) if author_match else ""
    
    # Extract date
    date_match = re.search(r'^Date: (.+)$', content, re.MULTILINE)
    date = date_match.group(1) if date_match else ""
    
    # Extract source URL
    source_match = re.search(r'^Source: (.+)$', content, re.MULTILINE)
    source = source_match.group(1) if source_match else ""
    
    # Find the main article content
    # First, try to find the main headline which usually starts after metadata
    headline_match = re.search(r'\n\n# ([^\n]+)\n\n', content)
    if headline_match:
        start_idx = headline_match.start()
        main_content = content[start_idx:]
    else:
        # If no headline found, extract everything after the metadata section
        content_match = re.search(r'\n\n([\s\S]+)$', content)
        main_content = content_match.group(1).strip() if content_match else ""
    
    # Clean up the content
    cleaned_content = clean_content(main_content)
    
    # Get the filename without path and extension
    filename = os.path.basename(file_path)
    
    return {
        "filename": filename,
        "title": title,
        "author": author,
        "date": date,
        "source": source,
        "clean_content": cleaned_content
    }

def process_directory(directory_path: str, output_format: str = "json", output_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Process all markdown files in a directory.
    
    Args:
        directory_path: Path to the directory containing markdown files
        output_format: Format for output (json or text)
        output_dir: Directory to save output files (if None, print to stdout)
        
    Returns:
        List of dictionaries with extracted data
    """
    results = []
    
    # Find all markdown files in the directory
    md_files = [f for f in os.listdir(directory_path) if f.endswith('.md') and f != "summary.md"]
    
    print(f"Found {len(md_files)} markdown files in {directory_path}")
    
    # Create output directory if needed
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Process each file
    for filename in md_files:
        file_path = os.path.join(directory_path, filename)
        print(f"Processing {filename}...")
        
        data = extract_and_clean_article(file_path)
        results.append(data)
        
        # Save individual file if output_dir is specified
        if output_dir:
            base_name = os.path.splitext(filename)[0]
            
            if output_format == "json":
                output_file = os.path.join(output_dir, f"{base_name}_clean.json")
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            else:  # text format
                output_file = os.path.join(output_dir, f"{base_name}_clean.txt")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"Title: {data['title']}\n")
                    f.write(f"Author: {data['author']}\n")
                    f.write(f"Date: {data['date']}\n")
                    f.write(f"Source: {data['source']}\n\n")
                    # Make sure clean_content doesn't end with [%
                    clean_content = data['clean_content']
                    if clean_content.endswith("[%"):
                        clean_content = clean_content[:-2]
                    f.write(clean_content)
    
    # Output the combined results if no output_dir is specified
    if not output_dir:
        if output_format == "json":
            output_data = {
                "timestamp": datetime.now().isoformat(),
                "count": len(results),
                "articles": results
            }
            print(json.dumps(output_data, indent=2))
        else:  # text format
            for idx, data in enumerate(results, 1):
                print(f"Article {idx}: {data['title']}")
                print(f"Author: {data['author']}")
                print(f"Date: {data['date']}")
                print(f"Source: {data['source']}")
                clean_content = data['clean_content']
                if clean_content.endswith("[%"):
                    clean_content = clean_content[:-2]
                print("\n" + clean_content)
                print("\n" + "="*50 + "\n")
    
    return results

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Extract and clean article content from markdown files")
    parser.add_argument("directory", help="Directory containing markdown files")
    parser.add_argument("--format", choices=["json", "text"], default="text",
                       help="Output format (json or text)")
    parser.add_argument("--output-dir", help="Output directory to save files")
    
    args = parser.parse_args()
    
    # Check if the directory exists
    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist")
        return 1
    
    process_directory(args.directory, args.format, args.output_dir)
    return 0

if __name__ == "__main__":
    sys.exit(main()) 