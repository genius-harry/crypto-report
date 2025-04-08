#!/usr/bin/env python
"""
Test Firecrawl functionality with a specific URL
"""

import os
import json
from dotenv import load_dotenv

# Import Firecrawl
try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    print("Firecrawl library not available. Install with: pip install firecrawl-py")
    exit(1)

# Load environment variables
load_dotenv()
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

if not FIRECRAWL_API_KEY:
    print("FIRECRAWL_API_KEY not found in .env file")
    exit(1)

def test_firecrawl(debug=True):
    """Test Firecrawl with a specific URL"""
    
    # URL to test
    url = 'https://www.financemagnates.com/cryptocurrency/bitcoin-ethereum-xrp-surge-as-fed-holds-interest-rates-steady/'
    
    print(f"Testing Firecrawl with URL: {url}")
    print(f"Using API key: {FIRECRAWL_API_KEY[:5]}...{FIRECRAWL_API_KEY[-5:]}")
    
    try:
        # Initialize Firecrawl client
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
        
        # Make request to Firecrawl
        print("Sending request to Firecrawl...")
        response = app.scrape_url(url=url, params={
            'formats': ['markdown'],
        })
        
        print("Response received!")
        
        # Debug output
        if debug:
            print("\nResponse type:", type(response))
            print("Response keys:", response.keys() if hasattr(response, 'keys') else "No keys (not a dict)")
            print("Response data:", response)
        
        # Check response
        if isinstance(response, dict):
            # If response is a dict, check for success field
            if 'success' in response and response['success']:
                content = response.get("data", {})
                
                # Print summary of content
                print("\nFirecrawl successfully extracted content:")
                print("-" * 50)
                print(f"Title: {content.get('title', 'N/A')}")
                print(f"Date: {content.get('date', 'N/A')}")
                print(f"Author: {content.get('author', 'N/A')}")
                print(f"Description: {content.get('description', 'N/A')[:100] if content.get('description') else 'N/A'}...")
                print(f"Markdown content length: {len(content.get('markdown', ''))}")
                
                # Save the response to a file
                with open("firecrawl_test_result.json", "w") as f:
                    json.dump(response, f, indent=2)
                print("-" * 50)
                print("Full response saved to firecrawl_test_result.json")
                
                return True
            else:
                print("Firecrawl failed!")
                print(f"Error: {response.get('message', 'No error message provided')}")
                return False
        else:
            # If response is not a dict, try to parse the content directly
            print("\nFirecrawl response is not a dictionary. Trying to extract content directly:")
            print("-" * 50)
            
            # Save the response to a file for inspection
            with open("firecrawl_test_result.json", "w") as f:
                json.dump({"raw_response": str(response)}, f, indent=2)
            
            print("Raw response saved to firecrawl_test_result.json")
            print("-" * 50)
            return False
    except Exception as e:
        print(f"Error testing Firecrawl: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_firecrawl(debug=True)
    if result:
        print("\nTest PASSED: Firecrawl is working correctly")
    else:
        print("\nTest FAILED: Firecrawl is not working correctly") 