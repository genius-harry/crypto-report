#!/bin/bash
# Script to run the Bitcoin.com News RSS-based crawler

# Default values
MAX_ARTICLES=10
MAX_FEEDS=1
OUTPUT_DIR="scraped_data"

# Function to display usage information
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -a, --articles N     Set maximum number of articles to fetch per feed (default: 10)"
    echo "  -f, --feeds N        Set maximum number of feeds to process (default: all)"
    echo "  -o, --output DIR     Set output directory (default: scraped_data)"
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
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

echo "Bitcoin.com News RSS Crawler"
echo "==========================="
echo "Max Articles per Feed: $MAX_ARTICLES"
echo "Max Feeds: $MAX_FEEDS"
echo "Output Directory: $OUTPUT_DIR"
echo "---------------------------"

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
pip install requests beautifulsoup4 html2text feedparser --quiet

# Run the crawler
echo "Starting RSS crawler..."
python bitcoincom_crawler.py -a $MAX_ARTICLES -f $MAX_FEEDS -o $OUTPUT_DIR

# Deactivate virtual environment
deactivate

echo "Crawling completed!" 