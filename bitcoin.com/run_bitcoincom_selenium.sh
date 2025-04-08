#!/bin/bash
# Script to run the Bitcoin.com News Selenium-based crawler

# Default values
MAX_ARTICLES=5
MAX_FEEDS=1
OUTPUT_DIR="scraped_data"
HEADLESS=true

# Function to display usage information
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -a, --articles N     Set maximum number of articles to fetch per feed (default: 5)"
    echo "  -f, --feeds N        Set maximum number of feeds to process (default: 1)"
    echo "  -o, --output DIR     Set output directory (default: scraped_data)"
    echo "  --no-headless        Run browser in non-headless mode (visible)"
    echo "  -h, --help           Display this help message"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--articles)
            MAX_ARTICLES="$2"
            shift 2
            ;;
        -f|--feeds)
            MAX_FEEDS="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --no-headless)
            HEADLESS=false
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

echo "Bitcoin.com News Selenium Crawler"
echo "================================="
echo "Max Articles per Feed: $MAX_ARTICLES"
echo "Max Feeds: $MAX_FEEDS"
echo "Output Directory: $OUTPUT_DIR"
echo "Headless Mode: $HEADLESS"
echo "---------------------------------"

# Check if virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install required packages
echo "Installing requirements..."
pip install requests beautifulsoup4 html2text feedparser selenium --quiet

# Check if ChromeDriver is installed
if ! command -v chromedriver &> /dev/null; then
    echo "Warning: ChromeDriver not found in PATH"
    echo "To install ChromeDriver:"
    echo "  Mac: brew install --cask chromedriver"
    echo "  Ubuntu: apt install chromium-chromedriver"
    echo "  Other: Download from https://sites.google.com/chromium.org/driver/"
fi

# Check if Chrome is installed
if ! command -v google-chrome &> /dev/null && ! command -v google-chrome-stable &> /dev/null && ! command -v chromium-browser &> /dev/null && [ ! -d "/Applications/Google Chrome.app" ] && [ ! -d "/Applications/Chrome.app" ]; then
    echo "Warning: Chrome browser not found"
    echo "Please install Chrome or Chromium browser"
fi

# Run the crawler
echo "Starting Selenium crawler..."
if [ "$HEADLESS" = true ]; then
    python bitcoincom_selenium_crawler.py -a $MAX_ARTICLES -f $MAX_FEEDS -o $OUTPUT_DIR
else
    python bitcoincom_selenium_crawler.py -a $MAX_ARTICLES -f $MAX_FEEDS -o $OUTPUT_DIR --no-headless
fi

# Deactivate virtual environment
deactivate

echo "Crawling completed!" 