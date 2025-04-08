#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

def main():
    print('Fetching page...')
    r = requests.get('https://u.today')
    print('Status:', r.status_code)
    
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Find news items
    news_items = soup.select('div.news__item')
    print(f'Found {len(news_items)} news items')
    
    if news_items:
        print('First item HTML structure:')
        print(news_items[0].prettify()[:500])
        
        # Check for title links
        for i, item in enumerate(news_items[:5]):  # Look at first 5 items
            print(f"\nItem #{i+1}")
            
            # Look for title link
            title_link = item.select_one('a.news__item-title')
            if title_link:
                print(f"Title link found: {title_link.get('href')}")
                print(f"Title text: {title_link.get_text(strip=True)[:50]}")
            else:
                print("No title link found")
                
                # Try to find any link
                all_links = item.find_all('a')
                print(f"Total links in item: {len(all_links)}")
                for j, link in enumerate(all_links):
                    print(f"  Link #{j+1}: {link.get('href')}")
                    print(f"  Text: {link.get_text(strip=True)[:30]}")
    
if __name__ == "__main__":
    main() 