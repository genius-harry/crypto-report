#!/bin/bash

# Create the main.py file
cat > main.py << 'EOF'
"""
Crypto News GraphRAG System

Main orchestration script that coordinates the entire process:
1. Search for crypto news
2. Rank news articles
3. Scrape news content
4. Build GraphRAG knowledge graph
5. Generate report
6. Render web interface

Run this script to execute the full pipeline.
"""

import os
import sys
import argparse
import signal
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Import modules
from modules.data_collection.search import search_crypto_news
from modules.data_collection.ranker import rank_articles
from modules.data_collection.scraper import scrape_articles
from modules.graph_builder.neo4j_connector import Neo4jConnector
from modules.graph_builder.schema import setup_schema, clean_schema
from modules.graph_builder.builder import build_graph
from modules.graph_builder.visualization import create_all_visualizations
from modules.report_generator.graphrag import setup_graphrag, generate_report
from modules.web_interface.app import start_web_interface

# Directory paths
OUTPUT_DIR = os.path.join(project_root, "output")
STATIC_DIR = os.path.join(project_root, "static")
TEMPLATES_DIR = os.path.join(project_root, "templates")
MARKDOWN_DIR = os.path.join(project_root, "markdown", "formatted")

# Ensure directories exist
for dir_path in [OUTPUT_DIR, STATIC_DIR, TEMPLATES_DIR, MARKDOWN_DIR]:
    os.makedirs(dir_path, exist_ok=True)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Crypto News GraphRAG System")
    
    parser.add_argument("--search", action="store_true", help="Search for new crypto news")
    parser.add_argument("--query", type=str, default="cryptocurrency news bitcoin ethereum", help="Search query")
    parser.add_argument("--limit", type=int, default=20, help="Number of articles to process")
    
    parser.add_argument("--clean", action="store_true", help="Clean Neo4j database before importing data")
    parser.add_argument("--skip-graph", action="store_true", help="Skip graph building (use existing data)")
    parser.add_argument("--skip-web", action="store_true", help="Skip web interface")
    
    parser.add_argument("--model", type=str, default="gpt-4", help="LLM model to use for report generation")
    
    return parser.parse_args()

def handle_interrupt(signum, frame):
    """Handle interrupt signal gracefully."""
    print("\n\nReceived interrupt signal. Shutting down...")
    sys.exit(0)

def find_latest_file(directory: str, prefix: str = "", suffix: str = ".json"):
    """Find the latest file with the given prefix and suffix in the directory."""
    if not os.path.exists(directory):
        return None
    
    matching_files = [
        f for f in os.listdir(directory) 
        if f.startswith(prefix) and f.endswith(suffix)
    ]
    
    if not matching_files:
        return None
    
    # Sort by creation time (newest first)
    matching_files.sort(
        key=lambda x: os.path.getmtime(os.path.join(directory, x)), 
        reverse=True
    )
    
    return os.path.join(directory, matching_files[0])

def search_phase(args):
    """
    Phase 1: Search for crypto news.
    
    Returns:
        List of search results
    """
    print("\n=== Phase 1: Search for Crypto News ===")
    
    if args.search:
        # Search for new articles
        print(f"Searching for crypto news with query: '{args.query}'")
        results = search_crypto_news(args.query, args.limit)
    else:
        # Use cached search results if available
        search_results_dir = os.path.join(project_root, "data", "search_results")
        latest_file = find_latest_file(search_results_dir, "crypto_news_search_")
        
        if latest_file and os.path.exists(latest_file):
            import json
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                results = data.get("results", [])
                print(f"Using cached search results: {latest_file}")
                print(f"Found {len(results)} results")
        else:
            print("No cached search results found. Performing new search.")
            results = search_crypto_news(args.query, args.limit)
    
    return results

def ranking_phase(search_results, args):
    """
    Phase 2: Rank news articles.
    
    Args:
        search_results: Search results from phase 1
        
    Returns:
        List of ranked articles
    """
    print("\n=== Phase 2: Rank News Articles ===")
    
    # Rank articles
    ranked_articles = rank_articles(search_results, use_ai=True, max_articles=args.limit)
    print(f"Ranked {len(ranked_articles)} articles")
    
    return ranked_articles

def scraping_phase(ranked_articles):
    """
    Phase 3: Scrape news content.
    
    Args:
        ranked_articles: Ranked articles from phase 2
        
    Returns:
        List of scraped articles
    """
    print("\n=== Phase 3: Scrape News Content ===")
    
    # Scrape articles
    scraped_articles = scrape_articles(ranked_articles)
    print(f"Scraped {len(scraped_articles)} articles")
    
    return scraped_articles

def graph_building_phase(scraped_articles, args):
    """
    Phase 4: Build GraphRAG knowledge graph.
    
    Args:
        scraped_articles: Scraped articles from phase 3
        
    Returns:
        Analytics results
    """
    print("\n=== Phase 4: Build GraphRAG Knowledge Graph ===")
    
    if args.skip_graph:
        print("Skipping graph building (using existing data)")
        return {}
    
    # Build the graph
    analytics = build_graph(scraped_articles, clear_existing=args.clean)
    
    # Create visualizations
    connector = Neo4jConnector()
    if connector.connect():
        create_all_visualizations(connector)
        connector.close()
    
    return analytics

def report_generation_phase(args):
    """
    Phase 5: Generate report.
    
    Args:
        args: Command line arguments
        
    Returns:
        Generated report
    """
    print("\n=== Phase 5: Generate Report ===")
    
    # Set up GraphRAG
    chain = setup_graphrag(args.model)
    
    if not chain:
        print("Failed to set up GraphRAG. Skipping report generation.")
        return ""
    
    # Generate report
    report = generate_report(chain, args.model)
    print(f"Generated report ({len(report)} characters)")
    
    return report

def web_interface_phase(report, scraped_articles, args):
    """
    Phase 6: Start web interface.
    
    Args:
        report: Generated report from phase 5
        scraped_articles: Scraped articles from phase 3
    """
    print("\n=== Phase 6: Start Web Interface ===")
    
    if args.skip_web:
        print("Skipping web interface")
        return
    
    # Extract article rankings for the web interface
    article_rankings = []
    for article in scraped_articles[:10]:  # Top 10 articles
        snippet = article.get("description", "")[:150] + "..." if article.get("description") else ""
        
        article_rankings.append({
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "snippet": snippet,
            "crypto_count": 0,  # This would be calculated based on the graph
            "topic_count": 0    # This would be calculated based on the graph
        })
    
    # Start web interface
    print("Starting web interface...")
    server_thread = start_web_interface(report, article_rankings)
    
    # Keep the main thread running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down web interface...")

def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Set up interrupt handler
    signal.signal(signal.SIGINT, handle_interrupt)
    
    print(f"Crypto News GraphRAG System")
    print(f"===========================")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Phase 1: Search for news
    search_results = search_phase(args)
    
    # Phase 2: Rank news
    ranked_articles = ranking_phase(search_results, args)
    
    # Phase 3: Scrape news
    scraped_articles = scraping_phase(ranked_articles)
    
    # Phase 4: Build GraphRAG
    analytics = graph_building_phase(scraped_articles, args)
    
    # Phase 5: Generate report
    report = report_generation_phase(args)
    
    # Phase 6: Start web interface
    web_interface_phase(report, scraped_articles, args)
    
    print(f"\nProcess completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
EOF

echo "Created main.py file." 