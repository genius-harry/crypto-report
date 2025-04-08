"""
Crypto News Search Module

This module handles searching for crypto news from various sources.
"""

import os
import json
from typing import Dict, List, Any
from datetime import datetime
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
SEARCH_API = os.getenv("SEARCH_API")
SEARCH_CX = os.getenv("SEARCH_CX")

def search_serpapi(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search for crypto news using SERPAPI.
    
    Args:
        query: Search query
        num_results: Number of results to return
        
    Returns:
        List of search results
    """
    url = "https://serpapi.com/search.json"
    
    params = {
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "engine": "google",
        "tbm": "nws",  # News search
        "num": num_results,
        "tbs": "qdr:w",  # Last week
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json()
        
        # Extract relevant information
        news_results = []
        if "news_results" in results:
            for item in results["news_results"]:
                news_results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "source": item.get("source", ""),
                    "date": item.get("date", ""),
                    "snippet": item.get("snippet", ""),
                })
        
        return news_results
    except Exception as e:
        print(f"Error searching with SERPAPI: {e}")
        return []

def search_google_custom(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search for crypto news using Google Custom Search API.
    
    Args:
        query: Search query
        num_results: Number of results to return
        
    Returns:
        List of search results
    """
    url = f"https://www.googleapis.com/customsearch/v1"
    
    params = {
        "q": query,
        "key": SEARCH_API,
        "cx": SEARCH_CX,
        "num": num_results,
        "sort": "date",
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json()
        
        # Extract relevant information
        news_results = []
        if "items" in results:
            for item in results["items"]:
                news_results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "source": item.get("displayLink", ""),
                    "date": item.get("snippet", "")[:10],  # Extract date from snippet if available
                    "snippet": item.get("snippet", ""),
                })
        
        return news_results
    except Exception as e:
        print(f"Error searching with Google Custom Search: {e}")
        return []

def merge_search_results(google_results: List[Dict[str, Any]], serpapi_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge search results from both Google and SERPAPI, removing duplicates based on URL.
    
    Args:
        google_results: Results from Google Custom Search API
        serpapi_results: Results from SERPAPI
        
    Returns:
        List of merged unique results
    """
    # Create a dictionary with URL as key to remove duplicates
    merged_dict = {}
    
    # Add Google results first
    for result in google_results:
        url = result.get("url", "")
        if url and url not in merged_dict:
            merged_dict[url] = result
    
    # Add SERPAPI results, skipping duplicates
    for result in serpapi_results:
        url = result.get("url", "")
        if url and url not in merged_dict:
            merged_dict[url] = result
    
    # Convert back to list
    return list(merged_dict.values())

def save_results_to_json(data: Dict[str, Any], filename: str, output_dir: str = "data"):
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save
        filename: Name of the file
        output_dir: Directory to save to
    
    Returns:
        Path to the saved file
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Saved data to {filepath}")
    return filepath

def search_crypto_news(query: str = "cryptocurrency news bitcoin ethereum", num_results: int = 20) -> List[Dict[str, Any]]:
    """
    Search for crypto news using multiple search engines and merge results.
    
    Args:
        query: Search query
        num_results: Number of results to return
        
    Returns:
        List of merged unique results
    """
    print(f"Searching for crypto news with query: '{query}'")
    
    # Search using Google Custom Search API
    google_results = search_google_custom(query, num_results)
    print(f"Found {len(google_results)} results from Google Custom Search")
    
    # Search using SERPAPI
    serpapi_results = search_serpapi(query, num_results)
    print(f"Found {len(serpapi_results)} results from SERPAPI")
    
    # Merge results
    merged_results = merge_search_results(google_results, serpapi_results)
    print(f"Merged into {len(merged_results)} unique results")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("data", "search_results")
    
    save_results_to_json(
        {"query": query, "timestamp": timestamp, "results": merged_results},
        f"crypto_news_search_{timestamp}.json",
        output_dir
    )
    
    return merged_results 