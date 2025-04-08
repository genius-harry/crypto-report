#!/bin/bash

# Default values
MAX_ARTICLES=10

# Function to display usage
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -a, --articles     Maximum number of articles to scrape (default: 10)"
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

# Edit the script to set max_articles
sed -i '' "s/links = fetch_article_links(max_articles=3)/links = fetch_article_links(max_articles=$MAX_ARTICLES)/" simple_crawler.py

# Run the crawler
echo "Running U.Today crawler (simple version)..."
python simple_crawler.py

# Restore the original max_articles
sed -i '' "s/links = fetch_article_links(max_articles=$MAX_ARTICLES)/links = fetch_article_links(max_articles=3)/" simple_crawler.py

# Deactivate virtual environment
deactivate

echo "Crawling completed!" 