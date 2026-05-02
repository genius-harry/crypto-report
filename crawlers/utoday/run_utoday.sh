#!/bin/bash

# Default values
MAX_ARTICLES=10
OUTPUT_DIR="scraped_data"

# Function to display usage
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -a, --articles     Maximum number of articles to scrape (default: 10)"
    echo "  -o, --output       Output directory (default: scraped_data)"
    echo "  -h, --help         Display this help message"
    exit 1
}

# Parse command line arguments
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

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install requests beautifulsoup4 html2text

# Run the crawler
echo "Running U.Today crawler..."
python utoday_crawler.py --output-dir "$OUTPUT_DIR" --max-articles "$MAX_ARTICLES"

# Deactivate virtual environment
deactivate

echo "Crawling completed!"
