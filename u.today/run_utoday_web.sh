#!/bin/bash

# This script runs the U.Today web crawler
# It accepts command line arguments for the number of articles to fetch and the output directory

# Default values
MAX_ARTICLES=5
OUTPUT_DIR="scraped_data"
VENV_DIR="venv"

# Parse command line arguments
while getopts ":a:o:h" opt; do
  case $opt in
    a)
      MAX_ARTICLES=$OPTARG
      ;;
    o)
      OUTPUT_DIR=$OPTARG
      ;;
    h)
      echo "Usage: $0 [-a MAX_ARTICLES] [-o OUTPUT_DIR]"
      echo "  -a MAX_ARTICLES   Maximum number of articles to fetch (default: $MAX_ARTICLES)"
      echo "  -o OUTPUT_DIR     Output directory (default: $OUTPUT_DIR)"
      echo "  -h                Display this help message"
      exit 0
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done

# Check if Python virtual environment exists, if not create one
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv $VENV_DIR
fi

# Activate virtual environment
source $VENV_DIR/bin/activate

# Install requirements if needed
echo "Installing requirements..."
pip install requests beautifulsoup4 html2text

# Run the crawler
echo "Running U.Today Web Crawler with max articles: $MAX_ARTICLES, output dir: $OUTPUT_DIR"
python3 utoday_web_crawler.py -a $MAX_ARTICLES -o $OUTPUT_DIR

# Deactivate virtual environment
deactivate

echo "Crawling completed!" 