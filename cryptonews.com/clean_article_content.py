#!/usr/bin/env python3
"""
Clean Article Content Processor

This script processes raw scraped articles from cryptonews.com and extracts 
the cleaned content, removing boilerplate text, ads, and formatting issues.
"""

import os
import re
import json
import argparse
from pathlib import Path
import glob
from typing import Dict, Any, List
from datetime import datetime

def clean_content(content: str) -> str:
    """
    Clean the article content by removing unwanted patterns.
    
    Args:
        content: The raw markdown content
        
    Returns:
        Cleaned content
    """
    # Remove extra whitespace and line breaks
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Remove common boilerplate text patterns from cryptonews.com
    patterns_to_remove = [
        # Social sharing buttons and similar sections
        r'Share\s+this\s+article',
        r'Follow\s+us\s+on\s+Twitter',
        r'Follow\s+us\s+on\s+Facebook',
        r'Follow\s+us\s+on\s+LinkedIn',
        r'Subscribe\s+to\s+our\s+newsletter',
        r'\[Image.*?\]',
        # Related article sections
        r'Related\s+Articles',
        r'You\s+might\s+also\s+like',
        r'Read\s+more',
        # Common advertisement patterns
        r'Advertisement',
        r'Sponsored',
        r'Promoted',
        # Footer and disclaimer text
        r'All Rights Reserved',
        r'Terms\s+and\s+Conditions',
        r'Privacy\s+Policy',
        r'Disclaimer:.*',
        # Repeated sections about the author
        r'About\s+the\s+[aA]uthor',
        # Join our Telegram channel text
        r'Join\s+our\s+Telegram\s+channel',
        # Links to download apps
        r'Download\s+our\s+app',
        # Cookie consent related text
        r'This\s+website\s+uses\s+cookies',
        # Comments section
        r'Comments',
        # Common copyright text
        r'©\s+\d{4}',
    ]
    
    # Compile the regex patterns for faster execution
    compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in patterns_to_remove]
    
    # Apply all patterns
    for pattern in compiled_patterns:
        content = pattern.sub('', content)
    
    # Remove URL references in markdown
    content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
    
    # Remove remaining markdown links if any still exist
    content = re.sub(r'\[[^\]]+\]', '', content)
    
    # Fix multiple spaces
    content = re.sub(r'\s{2,}', ' ', content)
    
    # Fix multiple newlines again (after other cleanups)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Remove leading/trailing whitespace from each line and overall
    content = '\n'.join(line.strip() for line in content.split('\n'))
    
    return content.strip()

def extract_metadata_from_markdown(filepath: str) -> Dict[str, Any]:
    """
    Extract metadata from a markdown file.
    
    Args:
        filepath: Path to the markdown file
        
    Returns:
        Dictionary with metadata including title, date, author, URL
    """
    metadata = {
        "title": "",
        "date": "",
        "author": "",
        "url": "",
        "source_file": filepath
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract title (first line after # or ##)
        title_match = re.search(r'#+ (.*?)(\n|$)', content)
        if title_match:
            metadata["title"] = title_match.group(1).strip()
        
        # Extract date
        date_match = re.search(r'Date: (.*?)(\n|$)', content)
        if date_match:
            metadata["date"] = date_match.group(1).strip()
        
        # Extract author
        author_match = re.search(r'Author: (.*?)(\n|$)', content)
        if author_match:
            metadata["author"] = author_match.group(1).strip()
        
        # Extract URL
        url_match = re.search(r'URL: (.*?)(\n|$)', content)
        if url_match:
            metadata["url"] = url_match.group(1).strip()
        
    except Exception as e:
        print(f"Error extracting metadata from {filepath}: {e}")
    
    return metadata

def clean_article_from_markdown(filepath: str, output_dir: str = None) -> Dict[str, Any]:
    """
    Process and clean a markdown article file.
    
    Args:
        filepath: Path to the markdown file
        output_dir: Optional directory to save the cleaned file
        
    Returns:
        Dictionary with metadata and clean content
    """
    result = extract_metadata_from_markdown(filepath)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract the main content (after metadata)
        # Look for the empty line after URL which separates metadata from content
        parts = content.split("URL: ")
        if len(parts) > 1:
            url_and_content = parts[1]
            content_parts = url_and_content.split("\n\n", 1)
            if len(content_parts) > 1:
                main_content = content_parts[1]
            else:
                main_content = ""
        else:
            main_content = content
        
        # Clean the content
        cleaned_content = clean_content(main_content)
        result["content"] = cleaned_content
        
        # Save cleaned file if output directory is provided
        if output_dir:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # Create a filename based on the original
            basename = os.path.basename(filepath)
            filename = os.path.splitext(basename)[0] + "_clean.txt"
            output_path = os.path.join(output_dir, filename)
            
            # Create a clean text file with metadata and content
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"Title: {result['title']}\n")
                f.write(f"Author: {result['author']}\n")
                f.write(f"Date: {result['date']}\n")
                f.write(f"Source URL: {result['url']}\n\n")
                f.write(cleaned_content)
            
            result["cleaned_file"] = output_path
        
    except Exception as e:
        print(f"Error cleaning article {filepath}: {e}")
        result["error"] = str(e)
    
    return result

def process_directory(input_dir: str, output_dir: str = None) -> List[Dict[str, Any]]:
    """
    Process all markdown files in a directory.
    
    Args:
        input_dir: Input directory containing markdown files
        output_dir: Optional directory to save cleaned files
        
    Returns:
        List of results for each processed file
    """
    if not output_dir:
        # Create a default output directory
        output_dir = os.path.join(os.path.dirname(input_dir), "clean_articles")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all .md files in input directory
    markdown_files = glob.glob(os.path.join(input_dir, "**", "*.md"), recursive=True)
    
    results = []
    for filepath in markdown_files:
        print(f"Processing {filepath}...")
        result = clean_article_from_markdown(filepath, output_dir)
        results.append(result)
    
    # Save summary
    summary = {
        "processed_at": datetime.now().isoformat(),
        "files_processed": len(results),
        "output_directory": output_dir,
        "results": results
    }
    
    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Processed {len(results)} files. Cleaned content saved to {output_dir}")
    return results

def main():
    """Parse arguments and run the article cleaner."""
    parser = argparse.ArgumentParser(description="Clean and process scraped articles")
    parser.add_argument("--input-dir", required=True, help="Directory containing scraped markdown files")
    parser.add_argument("--output-dir", help="Directory to save cleaned articles (default: input_dir/../clean_articles)")
    
    args = parser.parse_args()
    
    process_directory(args.input_dir, args.output_dir)

if __name__ == "__main__":
    main() 