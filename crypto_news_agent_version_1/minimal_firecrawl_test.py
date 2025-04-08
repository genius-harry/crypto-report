#!/usr/bin/env python
"""
Minimal Firecrawl test with the exact code provided by the user
"""

from firecrawl import FirecrawlApp

# Initialize app with the provided API key
app = FirecrawlApp(api_key='fc-ed2e73fc514f453db9fcadee0050e6c7')

# Make the request
print("Sending request to Firecrawl...")
response = app.scrape_url(url='https://docs.mendable.ai', params={
    'formats': ['markdown'],
})

# Print the response
print("\nResponse received!")
print(f"Response type: {type(response)}")
print(f"Response data (preview): {str(response)[:500]}...")

# Save response to file
import json
with open("minimal_firecrawl_result.json", "w") as f:
    try:
        json.dump(response, f, indent=2)
    except TypeError:
        json.dump({"raw_response": str(response)}, f, indent=2)

print("\nFull response saved to minimal_firecrawl_result.json") 