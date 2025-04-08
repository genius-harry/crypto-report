#!/bin/bash

# Default values
MAX_ARTICLES=10
OUTPUT_DIR="scraped_data"

# Function to display usage information
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -a, --articles NUM    Maximum number of articles to fetch (default: 10)"
    echo "  -o, --output DIR      Output directory for scraped data (default: scraped_data)"
    echo "  -h, --help            Display this help message and exit"
    echo ""
    exit 1
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--articles)
            MAX_ARTICLES="$2"
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

# Validate arguments
if ! [[ "$MAX_ARTICLES" =~ ^[0-9]+$ ]]; then
    echo "Error: Number of articles must be a positive integer"
    usage
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install required packages
echo "Installing requirements..."
pip install feedparser requests beautifulsoup4 html2text

# Run the crawler
echo "Starting BeInCrypto crawler..."
python beincrypto_crawler.py --articles $MAX_ARTICLES --output $OUTPUT_DIR

# Deactivate virtual environment
deactivate

echo "Crawling completed!" 