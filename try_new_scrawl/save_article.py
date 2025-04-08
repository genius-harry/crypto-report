#!/usr/bin/env python3
"""
Save the scraped article from bs_test_result.json to a markdown file.
"""

import json
from datetime import datetime

# Load the test result
with open('bs_test_result.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Create directory if it doesn't exist
import os
os.makedirs('scraped_articles', exist_ok=True)

# Create a filename with timestamp
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f'scraped_articles/tether_btc_holdings_{timestamp}.md'

# Write the markdown file
with open(filename, 'w', encoding='utf-8') as f:
    f.write(f"# {data['metadata']['title']}\n\n")
    f.write(f"Source: {data['metadata']['url']}\n")
    f.write(f"Author: {data['metadata']['author']}\n")
    f.write(f"Date: {data['metadata']['date']}\n\n")
    f.write(data['markdown'])

print(f"Saved article to {filename}") 