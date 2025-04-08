#!/bin/bash
# Run script for BeInCrypto.com crawler
# This script sets up the environment and runs the crawler

# Default values
MAX_ARTICLES=10
OUTPUT_DIR="scraped_data"

# Function to display usage information
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -a, --articles NUMBER  Maximum number of articles to scrape (default: 10)"
    echo "  -o, --output DIR       Output directory for scraped articles (default: scraped_data)"
    echo "  -h, --help             Display this help message and exit"
    exit 1
}

# Parse command-line options
while [[ $# -gt 0 ]]; do
    case "$1" in
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

# Create the virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install required packages
echo "Installing requirements..."
pip install requests beautifulsoup4 html2text

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Run the crawler
echo "Running BeInCrypto.com crawler..."
python beincrypto_crawler.py -a "$MAX_ARTICLES" -o "$OUTPUT_DIR"

# Deactivate the virtual environment
echo "Crawling completed!"
deactivate 