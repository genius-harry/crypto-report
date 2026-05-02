#!/bin/bash
# Script to run The Block Crypto News crawler

# Default values
MAX_ARTICLES=5
CATEGORY="latest"
OUTPUT_DIR="scraped_data"
HEADLESS=true

# Function to display usage information
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -a, --articles N     Set maximum number of articles to fetch (default: 5)"
    echo "  -c, --category TYPE  Set category to crawl: latest, bitcoin, ethereum, defi, business, policy (default: latest)"
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
        -c|--category)
            CATEGORY="$2"
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

echo "The Block Crypto News Crawler"
echo "============================"
echo "Category: $CATEGORY"
echo "Max Articles: $MAX_ARTICLES"
echo "Output Directory: $OUTPUT_DIR"
echo "Headless Mode: $HEADLESS"
echo "----------------------------"

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
pip install requests beautifulsoup4 html2text selenium --quiet

# Check if ChromeDriver is installed
if ! command -v chromedriver &> /dev/null; then
    echo "Warning: ChromeDriver not found in PATH"
    echo "Note: Modern Selenium may still work with bundled drivers"
fi

# Check if Chrome is installed
if ! command -v google-chrome &> /dev/null && ! command -v google-chrome-stable &> /dev/null && ! command -v chromium-browser &> /dev/null && [ ! -d "/Applications/Google Chrome.app" ] && [ ! -d "/Applications/Chrome.app" ]; then
    echo "Warning: Chrome browser not found"
    echo "Please install Chrome or Chromium browser"
fi

# Run the crawler
echo "Starting crawler..."
if [ "$HEADLESS" = true ]; then
    python theblock_crawler.py -a $MAX_ARTICLES -c $CATEGORY -o $OUTPUT_DIR
else
    python theblock_crawler.py -a $MAX_ARTICLES -c $CATEGORY -o $OUTPUT_DIR --no-headless
fi

# Deactivate virtual environment
deactivate

echo "Crawling completed!" 