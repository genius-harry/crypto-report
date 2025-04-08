#!/usr/bin/env python3
"""
Script to save the HTML of CryptoNews.com for debugging purposes
"""

import os
import time
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def save_page_html():
    """Save the HTML of the homepage for debugging."""
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    try:
        driver = uc.Chrome(options=options)
        driver.get("https://cryptonews.com/")
        
        # Wait for page to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Wait a bit more to ensure JavaScript content loads
        time.sleep(5)
        
        # Save the page source
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
            
        print(f"Page saved to debug_page.html")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    save_page_html() 