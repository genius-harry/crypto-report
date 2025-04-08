import os
import requests
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_serpapi_key():
    """Get SERPAPI API key from environment variable."""
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY environment variable not set")
    return api_key

def search_crypto_news(query: str = None, num_results: int = 30, date_restrict: str = 'd1') -> List[Dict[str, Any]]:
    """
    Search for the latest crypto news using SERPAPI.
    
    Args:
        query (str, optional): Search query. If None, will use 'latest cryptocurrency news'.
        num_results (int): Number of results to fetch. Default is 30.
        date_restrict (str): Time restriction for results. Default is 'd1' (past day).
        
    Returns:
        List[Dict[str, Any]]: List of search results with url, title, snippet, source, etc.
    """
    api_key = get_serpapi_key()
    
    # Generate search query based on current date if not provided
    if query is None:
        today = datetime.now().strftime('%Y-%m-%d')
        query = f"{today} latest cryptocurrency news"
    
    # Configure search parameters
    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": num_results,
        "tbm": "nws",  # News search
        "tbs": f"qdr:{date_restrict}",  # Date restriction
    }
    
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("news_results", []):
            result = {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("source", ""),
                "published_date": item.get("date", ""),
                "thumbnail": item.get("thumbnail", ""),
                "query": query,
                "search_engine": "SERPAPI",
                "searched_at": datetime.now().isoformat()
            }
            results.append(result)
        
        return results
    
    except requests.exceptions.RequestException as e:
        print(f"Error searching with SERPAPI: {e}")
        return []

def save_search_results(results: List[Dict[str, Any]], output_dir: str = "data"):
    """
    Save search results to a JSON file.
    
    Args:
        results (List[Dict[str, Any]]): The search results
        output_dir (str): Directory to save output
        
    Returns:
        str: Path to the saved file
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create filename based on timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/serpapi_crypto_news_{timestamp}.json"
    
    # Save results to file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(results)} SERPAPI search results to {filename}")
    return filename

def main():
    """Main entry point for the SERPAPI search module."""
    # Set output directory relative to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "data")
    
    try:
        # Search for crypto news
        print("Searching for latest cryptocurrency news using SERPAPI...")
        results = search_crypto_news()
        
        # Save results
        if results:
            filename = save_search_results(results, output_dir)
            print(f"Successfully saved {len(results)} crypto news articles from SERPAPI.")
            return 0
        else:
            print("No crypto news articles found from SERPAPI search.")
            return 1
            
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())