#!/bin/bash
# Master script to run Bitcoin.com News crawlers

# Default values
MAX_ARTICLES=10
CATEGORY="news"
MAX_FEEDS=1
OUTPUT_DIR="scraped_data"
CRAWLER_TYPE="rss"  # Options: web, rss, selenium, all
HEADLESS=true

# Function to display usage information
usage() {
    echo "Bitcoin.com News Crawler - Master Script"
    echo "========================================"
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE      Crawler type: web, rss, selenium, all (default: rss)"
    echo "  -a, --articles N     Set maximum number of articles to fetch (default: 10)"
    echo "  -c, --category TYPE  Set category for web crawler: news, bitcoin, ethereum, altcoins (default: news)"
    echo "  -f, --feeds N        Set maximum number of feeds for RSS crawler (default: 1)"
    echo "  -o, --output DIR     Set output directory (default: scraped_data)"
    echo "  --no-headless        Run Selenium browser in non-headless mode (visible)"
    echo "  -h, --help           Display this help message"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            CRAWLER_TYPE="$2"
            shift 2
            ;;
        -a|--articles)
            MAX_ARTICLES="$2"
            shift 2
            ;;
        -c|--category)
            CATEGORY="$2"
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

# Validate crawler type
if [[ "$CRAWLER_TYPE" != "web" && "$CRAWLER_TYPE" != "rss" && "$CRAWLER_TYPE" != "selenium" && "$CRAWLER_TYPE" != "all" ]]; then
    echo "Error: Invalid crawler type. Must be 'web', 'rss', 'selenium', or 'all'."
    usage
fi

echo "Bitcoin.com News Crawler - Master Script"
echo "========================================"
echo "Crawler Type: $CRAWLER_TYPE"
echo "Max Articles: $MAX_ARTICLES"
echo "Category (web crawler): $CATEGORY"
echo "Max Feeds (RSS crawler): $MAX_FEEDS"
echo "Output Directory: $OUTPUT_DIR"
echo "Headless Mode: $HEADLESS"
echo "----------------------------------------"

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
if [[ "$CRAWLER_TYPE" == "selenium" || "$CRAWLER_TYPE" == "all" ]]; then
    pip install requests beautifulsoup4 html2text feedparser selenium --quiet
else
    pip install requests beautifulsoup4 html2text feedparser --quiet
fi

# Run the selected crawler(s)
if [[ "$CRAWLER_TYPE" == "web" || "$CRAWLER_TYPE" == "all" ]]; then
    echo ""
    echo "Starting web crawler..."
    echo "======================="
    python bitcoin_crawler.py -a $MAX_ARTICLES -c $CATEGORY -o $OUTPUT_DIR
    echo ""
fi

if [[ "$CRAWLER_TYPE" == "rss" || "$CRAWLER_TYPE" == "all" ]]; then
    echo ""
    echo "Starting RSS crawler..."
    echo "======================="
    python bitcoincom_crawler.py -a $MAX_ARTICLES -f $MAX_FEEDS -o $OUTPUT_DIR
    echo ""
fi

if [[ "$CRAWLER_TYPE" == "selenium" || "$CRAWLER_TYPE" == "all" ]]; then
    echo ""
    echo "Starting Selenium crawler..."
    echo "==========================="
    # Check if ChromeDriver is installed
    if ! command -v chromedriver &> /dev/null; then
        echo "Warning: ChromeDriver not found in PATH"
        echo "Note: Modern Selenium may still work with bundled drivers"
    fi
    
    # Check if Chrome is installed
    if ! command -v google-chrome &> /dev/null && ! command -v google-chrome-stable &> /dev/null && ! command -v chromium-browser &> /dev/null && [ ! -d "/Applications/Google Chrome.app" ] && [ ! -d "/Applications/Chrome.app" ]; then
        echo "Warning: Chrome browser not found"
    fi
    
    if [ "$HEADLESS" = true ]; then
        python bitcoincom_selenium_crawler.py -a $MAX_ARTICLES -f $MAX_FEEDS -o $OUTPUT_DIR
    else
        python bitcoincom_selenium_crawler.py -a $MAX_ARTICLES -f $MAX_FEEDS -o $OUTPUT_DIR --no-headless
    fi
    echo ""
fi

# Deactivate virtual environment
deactivate

echo "All crawling completed!" 