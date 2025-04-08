import os
import requests
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_google_search_api_key():
    """Get Google Search API key from environment variable."""
    api_key = os.environ.get("SEARCH_API")
    if not api_key:
        raise ValueError("SEARCH_API environment variable not set")
    return api_key

def get_google_search_cx():
    """Get Google Custom Search Engine ID from environment variable."""
    cx = os.environ.get("SEARCH_CX", "c636a0ae29e6346a0")
    return cx

def search_crypto_news(query: str = None, num_results: int = 30, date_restrict: str = 'd1') -> List[Dict[str, Any]]:
    """
    Search for the latest crypto news using Google Custom Search JSON API.
    
    Args:
        query (str, optional): Search query. If None, will use 'latest cryptocurrency news'.
        num_results (int): Number of results to fetch. Default is 30.
        date_restrict (str): Time restriction for results. Default is 'd1' (past day).
        
    Returns:
        List[Dict[str, Any]]: List of search results with url, title, snippet, source, etc.
    """
    api_key = get_google_search_api_key()
    cx = get_google_search_cx()
    
    # Generate search query based on current date if not provided
    if query is None:
        today = datetime.now().strftime('%Y-%m-%d')
        query = f"{today} latest cryptocurrency news"
    
    # Results will be collected here
    all_results = []
    
    # Google Custom Search only returns 10 results per request, so we need to make multiple requests
    for start_index in range(1, num_results + 1, 10):
        # Configure search parameters
        params = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "start": start_index,
            "num": min(10, num_results - start_index + 1),  # Can't request more than 10 at once
            "dateRestrict": date_restrict,
            "sort": "date",  # Sort by date to get the latest news
        }
        
        try:
            response = requests.get("https://www.googleapis.com/customsearch/v1", params=params)
            response.raise_for_status()
            data = response.json()
            
            if "items" not in data:
                print(f"No results found for request starting at index {start_index}")
                break
                
            for item in data["items"]:
                result = {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": item.get("displayLink", ""),
                    "published_date": item.get("pagemap", {}).get("metatags", [{}])[0].get("article:published_time", ""),
                    "thumbnail": item.get("pagemap", {}).get("cse_thumbnail", [{}])[0].get("src", "") if "pagemap" in item and "cse_thumbnail" in item["pagemap"] else "",
                    "query": query,
                    "search_engine": "Google Custom Search",
                    "searched_at": datetime.now().isoformat()
                }
                all_results.append(result)
            
            # If we've reached the end of results or collected enough, break
            if len(all_results) >= num_results or "nextPage" not in data.get("queries", {}):
                break
            
            # Add a small delay to avoid rate limiting
            import time
            time.sleep(0.5)
            
        except requests.exceptions.RequestException as e:
            print(f"Error searching with Google Custom Search API: {e}")
            break
    
    return all_results

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
    filename = f"{output_dir}/google_crypto_news_{timestamp}.json"
    
    # Save results to file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(results)} Google search results to {filename}")
    return filename

def main():
    """Main entry point for the Google Search module."""
    # Set output directory relative to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "data")
    
    try:
        # Search for crypto news
        print("Searching for latest cryptocurrency news using Google Custom Search API...")
        results = search_crypto_news()
        
        # Save results
        if results:
            filename = save_search_results(results, output_dir)
            print(f"Successfully saved {len(results)} crypto news articles from Google Custom Search.")
            return 0
        else:
            print("No crypto news articles found from Google Custom Search.")
            return 1
            
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())