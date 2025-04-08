#!/usr/bin/env python3

import os
import time
import requests
from bs4 import BeautifulSoup
import html2text
from datetime import datetime
import json
import re
from pathlib import Path

# Configure HTML to Text converter
h2t = html2text.HTML2Text()
h2t.ignore_links = False
h2t.ignore_images = False
h2t.ignore_tables = False
h2t.body_width = 0  # No wrapping

def fetch_article_links(max_articles=5):
    print("Fetching article links...")
    r = requests.get("https://u.today")
    soup = BeautifulSoup(r.text, "html.parser")
    
    news_items = soup.select("div.news__item")
    print(f"Found {len(news_items)} news items")
    
    links = []
    for item in news_items:
        for link in item.find_all("a"):
            if link.has_attr("href") and "news__item-body" in str(link.get("class", [])):
                url = link["href"]
                if url.startswith("http"):
                    links.append(url)
                    print(f"Found link: {url}")
                    break
    
    # Filter duplicates
    links = list(dict.fromkeys(links))
    print(f"Found {len(links)} unique article links")
    
    return links[:max_articles]

def fetch_article(url):
    print(f"Fetching article: {url}")
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    
    # Extract title
    title = ""
    title_elem = soup.select_one("h1")
    if title_elem:
        title = title_elem.get_text().strip()
        print(f"Found title: {title}")
    
    # Extract date
    date = ""
    date_elem = soup.select_one("div.article__info time")
    if date_elem:
        date = date_elem.get_text().strip()
        print(f"Found date: {date}")
    
    # Extract author
    author = ""
    author_elem = soup.select_one("div.article__author-name a")
    if author_elem:
        author = author_elem.get_text().strip()
        print(f"Found author: {author}")
    
    # Extract content
    content = ""
    content_elem = soup.select_one("div.article__content")
    if content_elem:
        for elem in content_elem.select("script, style, div.social-share, div.related-posts, div.tags"):
            elem.decompose()
        
        content = h2t.handle(str(content_elem))
        print("Successfully extracted content")
    
    return {
        "url": url,
        "title": title,
        "date": date,
        "author": author,
        "content": content,
        "success": bool(content)
    }

def save_article(article, output_dir):
    if not article["success"]:
        return None
    
    # Create safe filename
    safe_title = re.sub(r'[^a-zA-Z0-9]+', '_', article["title"].lower())
    if len(safe_title) > 50:
        safe_title = safe_title[:50]
    safe_title = safe_title.rstrip('_')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{safe_title}"
    
    # Create directories
    md_dir = os.path.join(output_dir, "markdown")
    json_dir = os.path.join(output_dir, "json")
    os.makedirs(md_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)
    
    # Save as markdown
    md_path = os.path.join(md_dir, f"{filename}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {article['title']}\n\n")
        if article["date"]:
            f.write(f"**Date:** {article['date']}\n\n")
        if article["author"]:
            f.write(f"**Author:** {article['author']}\n\n")
        f.write(f"**Source:** [{article['url']}]({article['url']})\n\n")
        f.write(article["content"])
    
    # Save as JSON
    json_path = os.path.join(json_dir, f"{filename}.json")
    json_data = {
        "title": article["title"],
        "date": article["date"],
        "author": article["author"],
        "url": article["url"],
        "content": article["content"]
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"Article saved: {md_path}")
    return md_path

def main():
    # Create timestamp-based output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("scraped_data", timestamp)
    os.makedirs(output_dir, exist_ok=True)
    
    # Fetch article links
    links = fetch_article_links(max_articles=3)
    
    if not links:
        print("No article links found.")
        return
    
    successful = 0
    failed = 0
    
    # Process each article
    for url in links:
        # Fetch and process article
        article = fetch_article(url)
        
        # Save article
        if article["success"]:
            save_article(article, output_dir)
            successful += 1
        else:
            failed += 1
        
        # Wait between requests
        time.sleep(2)
    
    # Save summary
    summary = {
        "timestamp": timestamp,
        "articles_fetched": len(links),
        "successful": successful,
        "failed": failed
    }
    
    with open(os.path.join(output_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nCrawling completed. Results saved to {output_dir}")
    print(f"Articles fetched: {len(links)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

if __name__ == "__main__":
    main() 