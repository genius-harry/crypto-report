
# Example code for integrating Beautiful Soup crawler with existing pipeline

from try_new_scrawl.bs_crawler import scrape_article

def scrape_with_beautiful_soup(url: str):
    """Scrape a URL using the Beautiful Soup crawler."""
    return scrape_article(url)

# Example of modifying the existing scraper.py to use Beautiful Soup as an alternative
def scrape_url(url: str):
    """Scrape a URL using available scrapers."""
    # Try Firecrawl first if available
    if FIRECRAWL_AVAILABLE and FIRECRAWL_API_KEY:
        try:
            print(f"Using Firecrawl for {url}")
            scraped = scrape_url_with_firecrawl(url)
            
            # Check if Firecrawl succeeded
            if not scraped.get("error"):
                return scraped
                
            print(f"Firecrawl failed, trying Beautiful Soup: {scraped.get('error')}")
        except Exception as e:
            print(f"Firecrawl error: {str(e)}")
    
    # Try Beautiful Soup crawler
    try:
        print(f"Using Beautiful Soup for {url}")
        # Import the Beautiful Soup crawler
        from try_new_scrawl.bs_crawler import scrape_article
        
        # Scrape with Beautiful Soup
        result = scrape_article(url)
        
        if result:
            # Format the result to match the expected structure
            return {
                "url": url,
                "title": result["metadata"].get("title", ""),
                "date": result["metadata"].get("date", ""),
                "author": result["metadata"].get("author", ""),
                "description": result["metadata"].get("description", ""),
                "content": result.get("content", ""),
                "markdown": result.get("markdown", ""),
                "image": result["metadata"].get("image", ""),
                "source": result["metadata"].get("source", "")
            }
            
        print(f"Beautiful Soup failed, trying requests fallback")
    except Exception as e:
        print(f"Beautiful Soup error: {str(e)}")
    
    # Fallback to requests if both Firecrawl and Beautiful Soup failed
    return scrape_url_with_requests(url)
