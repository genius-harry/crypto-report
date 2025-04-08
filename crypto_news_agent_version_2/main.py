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
import json

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
from modules.graph_builder.import_coinapi import fetch_coinapi_data, import_coinapi_data_to_neo4j

# Directory paths
OUTPUT_DIR = os.path.join(project_root, "output")
STATIC_DIR = os.path.join(project_root, "static")
TEMPLATES_DIR = os.path.join(project_root, "templates")
MARKDOWN_DIR = os.path.join(project_root, "markdown", "formatted")

# Ensure directories exist
for dir_path in [OUTPUT_DIR, STATIC_DIR, TEMPLATES_DIR, MARKDOWN_DIR]:
    os.makedirs(dir_path, exist_ok=True)

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Crypto News GraphRAG System")
    parser.add_argument("--search", action="store_true", help="Force new search")
    parser.add_argument("--skip-search", action="store_true", help="Skip search phase")
    parser.add_argument("--skip-rank", action="store_true", help="Skip ranking phase")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip scraping phase")
    parser.add_argument("--skip-graph", action="store_true", help="Skip graph building")
    parser.add_argument("--skip-report", action="store_true", help="Skip report generation")
    parser.add_argument("--skip-web", action="store_true", help="Skip web interface")
    parser.add_argument("--clean", action="store_true", help="Clean database before import")
    parser.add_argument("--model", type=str, default="gpt-4o", help="LLM model to use")
    parser.add_argument("--query", type=str, default="cryptocurrency news bitcoin ethereum", help="Search query")
    parser.add_argument("--limit", type=int, default=20, help="Number of articles to process (default: 20)")
    parser.add_argument("--scrape-limit", type=int, default=None, help="Max number of articles to scrape (default: same as limit)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--port", type=int, default=5001, help="Port for web interface (default: 5001)")
    
    # Add options for running individual phases
    phase_group = parser.add_argument_group('Phase control')
    phase_group.add_argument("--only-search", action="store_true", help="Only run phase 1: Search for news")
    phase_group.add_argument("--only-rank", action="store_true", help="Only run phase 2: Rank news")
    phase_group.add_argument("--only-scrape", action="store_true", help="Only run phase 3: Scrape news")
    phase_group.add_argument("--only-graph", action="store_true", help="Only run phase 4: Build graph")
    phase_group.add_argument("--only-report", action="store_true", help="Only run phase 5: Generate report")
    phase_group.add_argument("--only-web", action="store_true", help="Only run phase 6: Web interface")
    phase_group.add_argument("--phases", type=str, help="Comma-separated list of phases to run (1-6)")
    
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
    """Rank news articles by relevance."""
    print("\n=== Phase 2: Rank News Articles ===")
    ranked_articles = rank_articles(search_results, use_ai=True, max_articles=args.limit, verbose=args.verbose)
    print(f"Ranked {len(ranked_articles)} articles")
    return ranked_articles

def scraping_phase(ranked_articles, args):
    """
    Phase 3: Scrape news content.
    
    Args:
        ranked_articles: Ranked articles from phase 2
        args: Command line arguments with verbose flag
        
    Returns:
        List of scraped articles
    """
    print("\n=== Phase 3: Scrape News Content ===")
    
    # Apply scrape limit if specified
    articles_to_scrape = ranked_articles
    scrape_limit = args.scrape_limit if args.scrape_limit is not None else args.limit
    
    if len(ranked_articles) > scrape_limit:
        print(f"Limiting scraping to top {scrape_limit} articles (out of {len(ranked_articles)} ranked)")
        articles_to_scrape = ranked_articles[:scrape_limit]
    
    # Scrape articles
    scraped_articles = scrape_articles(articles_to_scrape, verbose=args.verbose)
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
    
    # Import CoinAPI data
    print("\n=== Importing CoinAPI Data to Knowledge Graph ===")
    coinapi_data = fetch_coinapi_data()
    if coinapi_data:
        if import_coinapi_data_to_neo4j(coinapi_data):
            print("CoinAPI data import completed successfully")
        else:
            print("CoinAPI data import failed")
    else:
        print("No CoinAPI data to import")
    
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

def web_interface_phase(args, report=None, article_rankings=None):
    """Phase 6: Start Web Interface"""
    print("=== Phase 6: Start Web Interface ===")
    
    print(f"Starting web interface on port {args.port}...")
    
    # Import here to avoid circular imports
    from modules.web_interface.app import start_web_interface
    
    # Start the web interface
    start_web_interface(port=args.port)
    
    return True

def main():
    """Main entry point for the Crypto News GraphRAG system."""
    start_time = datetime.now()
    
    # Print header
    print("Crypto News GraphRAG System")
    print("===========================")
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Determine which phases to run based on args
    should_run_phase = [True] * 6  # Default: run all phases
    
    # Handle --only flags
    only_flags = False
    if args.only_search:
        should_run_phase = [True, False, False, False, False, False]
        only_flags = True
    if args.only_rank:
        should_run_phase = [True, True, False, False, False, False]
        only_flags = True
    if args.only_scrape:
        should_run_phase = [True, True, True, False, False, False]
        only_flags = True
    if args.only_graph:
        should_run_phase = [False, False, False, True, False, False]
        only_flags = True
    if args.only_report:
        should_run_phase = [False, False, False, False, True, False]
        only_flags = True
    if args.only_web:
        should_run_phase = [False, False, False, False, False, True]
        only_flags = True
        
    # Handle --skip flags (if no --only flags are set)
    if not only_flags:
        if args.skip_search:
            should_run_phase[0] = False
        if args.skip_rank:
            should_run_phase[1] = False
        if args.skip_scrape:
            should_run_phase[2] = False
        if args.skip_graph:
            should_run_phase[3] = False
        if args.skip_report:
            should_run_phase[4] = False
        if args.skip_web:
            should_run_phase[5] = False
    
    # Initialize variables
    search_results = None
    ranked_articles = None
    scraped_articles = None
    report = None
    graph_data = None
    
    # Phase 1: Search
    if should_run_phase[0]:
        search_results = search_phase(args)
    
    # Phase 2: Rank
    if should_run_phase[1]:
        if search_results:
            ranked_articles = ranking_phase(search_results, args)
        elif os.path.exists("data/search_results"):
            print("\n=== Loading cached search results ===")
            search_dir = "data/search_results"
            files = sorted([os.path.join(search_dir, f) for f in os.listdir(search_dir)
                           if f.startswith('crypto_news_search_')], key=os.path.getmtime, reverse=True)
            
            if files:
                with open(files[0], 'r') as f:
                    search_results = json.load(f)
                print(f"Loaded {len(search_results)} results from {files[0]}")
                ranked_articles = ranking_phase(search_results, args)
            else:
                print("No cached search results found. Please run with --only-search first.")
                return
        else:
            print("Cannot rank without search results. Run phase 1 first or provide cached results.")
            return
    elif should_run_phase[2] or should_run_phase[3] or should_run_phase[4] or should_run_phase[5]:
        # If we need ranked articles for later phases but are skipping phase 2
        ranked_dir = os.path.join("data", "ranked")
        if os.path.exists(ranked_dir):
            files = sorted([os.path.join(ranked_dir, f) for f in os.listdir(ranked_dir)
                           if f.startswith('ranked_articles_')], key=os.path.getmtime, reverse=True)
            
            if files:
                print("\n=== Loading cached ranked articles ===")
                with open(files[0], 'r') as f:
                    ranked_articles = json.load(f)
                print(f"Loaded {len(ranked_articles)} ranked articles from {files[0]}")
            elif should_run_phase[2]:  # Only error if we need it for scraping
                print("No cached ranked articles found. Please run with --only-rank first.")
                return
    
    # Phase 3: Scrape
    if should_run_phase[2]:
        if ranked_articles:
            scraped_articles = scraping_phase(ranked_articles, args)
        else:
            print("Cannot scrape without ranked articles. Run phase 2 first or provide cached results.")
            return
    # If we're only running web or graph or report, ensure we have scraped articles
    elif should_run_phase[3] or should_run_phase[4] or should_run_phase[5]:
        # If skipping scrape but need results for later phases, load from file
        scraped_dir = os.path.join("data", "articles")
        if os.path.exists(scraped_dir):
            files = sorted([os.path.join(scraped_dir, f) for f in os.listdir(scraped_dir)
                        if f.startswith('scraped_articles_')], key=os.path.getmtime, reverse=True)
            
            if files:
                print("\n=== Loading cached scraped articles ===")
                with open(files[0], 'r') as f:
                    scraped_articles = json.load(f)
                print(f"Loaded scraped articles from {files[0]}")
            else:
                print("No cached scraped articles found. Please run with --only-scrape first.")
                return
        else:
            print("No cached scraped articles found. Please run with --only-scrape first.")
            return
    
    # Phase 4: Build graph
    if should_run_phase[3]:
        if scraped_articles:
            graph_data = graph_building_phase(scraped_articles.get("articles", []) if isinstance(scraped_articles, dict) else scraped_articles, args)
        else:
            print("Cannot build graph without scraped articles. Run phase 3 first or provide cached results.")
            return
    
    # Phase 5: Generate report
    if should_run_phase[4]:
        report = report_generation_phase(args)
    
    # Phase 6: Start web interface
    if should_run_phase[5]:
        web_interface_phase(args, report, None)
    
    # Print completion message
    end_time = datetime.now()
    duration = end_time - start_time
    print("\nCrypto News GraphRAG System completed")
    print(f"Duration: {duration}")
    print(f"Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
