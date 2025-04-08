#!/usr/bin/env python3
"""
Extract Article Data

This script extracts title, author, and content from markdown files
created by the CoinDesk crawler.
"""

import os
import json
import re
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

def extract_data_from_markdown(file_path: str) -> Dict[str, Any]:
    """
    Extract title, author, and content from a markdown file.
    
    Args:
        file_path: Path to the markdown file
        
    Returns:
        Dictionary with extracted data
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
    
    # Extract description
    description_match = re.search(r'^Description: (.+)$', content, re.MULTILINE)
    description = description_match.group(1) if description_match else ""
    
    # Extract source URL
    source_match = re.search(r'^Source: (.+)$', content, re.MULTILINE)
    source = source_match.group(1) if source_match else ""
    
    # Extract main content (everything after the metadata section)
    # The metadata section ends with a blank line
    content_match = re.search(r'\n\n([\s\S]+)$', content)
    article_content = content_match.group(1).strip() if content_match else ""
    
    # Get the filename without path and extension
    filename = os.path.basename(file_path)
    
    return {
        "filename": filename,
        "title": title,
        "author": author,
        "date": date,
        "description": description,
        "source": source,
        "content": article_content
    }

def process_directory(directory_path: str, output_format: str = "json", output_file: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Process all markdown files in a directory.
    
    Args:
        directory_path: Path to the directory containing markdown files
        output_format: Format for output (json or summary)
        output_file: Path to save output file (if None, print to stdout)
        
    Returns:
        List of dictionaries with extracted data
    """
    results = []
    
    # Find all markdown files in the directory
    md_files = [f for f in os.listdir(directory_path) if f.endswith('.md') and f != "summary.md"]
    
    print(f"Found {len(md_files)} markdown files in {directory_path}")
    
    # Process each file
    for filename in md_files:
        file_path = os.path.join(directory_path, filename)
        print(f"Processing {filename}...")
        
        data = extract_data_from_markdown(file_path)
        results.append(data)
    
    # Output the results in the specified format
    if output_format == "json":
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "count": len(results),
            "articles": results
        }
        
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2)
            print(f"Saved output to {output_file}")
        else:
            print(json.dumps(output_data, indent=2))
    else:  # summary format
        summary_text = f"Article Extraction Summary\n{'='*25}\n\n"
        summary_text += f"Processed {len(results)} articles\n\n"
        
        for idx, data in enumerate(results, 1):
            summary_text += f"{idx}. {data['title']}\n"
            summary_text += f"   Author: {data['author']}\n"
            summary_text += f"   Date: {data['date']}\n"
            summary_text += f"   Content length: {len(data['content'])} characters\n\n"
        
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(summary_text)
            print(f"Saved summary to {output_file}")
        else:
            print(summary_text)
    
    return results

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Extract data from markdown files")
    parser.add_argument("directory", help="Directory containing markdown files")
    parser.add_argument("--format", choices=["json", "summary"], default="json",
                       help="Output format (json or summary)")
    parser.add_argument("--output", help="Output file path (defaults to stdout)")
    
    args = parser.parse_args()
    
    # Check if the directory exists
    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist")
        return 1
    
    process_directory(args.directory, args.format, args.output)
    return 0

if __name__ == "__main__":
    sys.exit(main()) 