#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

print("Fetching page...")
r = requests.get("https://u.today")
print("Status:", r.status_code)

soup = BeautifulSoup(r.text, "html.parser")
news_items = soup.select("div.news__item")
print(f"Found {len(news_items)} news items")

if news_items:
    # Check first item
    print("\nFirst item classes:", news_items[0].get("class"))
    
    # Check links in first 3 items
    for i, item in enumerate(news_items[:3]):
        print(f"\nItem #{i+1}")
        links = item.find_all("a")
        print(f"Links in item: {len(links)}")
        
        for j, link in enumerate(links):
            print(f"  Link #{j+1}: {link.get('href')}")
            print(f"  Text: {link.get_text(strip=True)[:30]}")
            print(f"  Classes: {link.get('class')}")
