#!/bin/bash
#
# Improved CryptoNews.com Crawler Runner
#
# This script simplifies running the CryptoNews.com crawler with custom parameters
# and includes better error handling, logging, and support for both RSS and Selenium crawlers.

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
CRAWLER_TYPE="selenium"  # Default to Selenium crawler as it's more robust
MAX_ARTICLES=10
MAX_FEEDS=4
MAX_SECTIONS=3
MAX_RETRIES=3
HEADLESS=true
OUTPUT_DIR="scraped_data"
VISIBLE_BROWSER=""
DEBUG_MODE=""
PYTHON_CMD="python3"

# Function to display usage
usage() {
    echo -e "${BLUE}Usage:${NC} $0 [options]"
    echo -e "${BLUE}Options:${NC}"
    echo "  -t, --type         Crawler type: 'rss' or 'selenium' (default: selenium)"
    echo "  -a, --articles     Maximum number of articles to scrape (default: 10)"
    echo "  -f, --feeds        Maximum number of RSS feeds to process (default: 4)"
    echo "  -s, --sections     Maximum number of sections to scrape (for selenium crawler) (default: 3)"
    echo "  -r, --retries      Maximum number of retries (default: 3)"
    echo "  -o, --output       Output directory (default: scraped_data)"
    echo "  -v, --visible      Run selenium crawler with visible browser"
    echo "  -d, --debug        Enable debug mode for more verbose output"
    echo "  -h, --help         Display this help message"
    echo
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 --type selenium --articles 5 --visible"
    echo "  $0 --type rss --articles 20 --feeds 2"
}

# Function to log messages
log() {
    local level=$1
    local message=$2
    local color=$NC
    
    case $level in
        "INFO") color=$GREEN ;;
        "WARN") color=$YELLOW ;;
        "ERROR") color=$RED ;;
    esac
    
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message${NC}"
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
        -f|--feeds)
            MAX_FEEDS="$2"
            shift 2
            ;;
        -s|--sections)
            MAX_SECTIONS="$2"
            shift 2
            ;;
        -r|--retries)
            MAX_RETRIES="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -v|--visible)
            VISIBLE_BROWSER="--visible"
            HEADLESS=false
            shift
            ;;
        -d|--debug)
            DEBUG_MODE="--debug"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate crawler type
if [[ "$CRAWLER_TYPE" != "rss" && "$CRAWLER_TYPE" != "selenium" ]]; then
    log "ERROR" "Invalid crawler type. Must be 'rss' or 'selenium'"
    exit 1
fi

# Check Python installation
if ! command -v $PYTHON_CMD &>/dev/null; then
    log "ERROR" "Python 3 is not installed or not in PATH"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    log "INFO" "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        log "ERROR" "Failed to create virtual environment. Please install venv package."
        exit 1
    fi
fi

# Activate virtual environment
log "INFO" "Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    log "ERROR" "Failed to activate virtual environment"
    exit 1
fi

# Check and install requirements
if [ -f "requirements.txt" ]; then
    log "INFO" "Installing requirements..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        log "ERROR" "Failed to install required packages"
        exit 1
    fi
else
    log "WARN" "requirements.txt not found, installing minimal requirements..."
    pip install beautifulsoup4 feedparser requests html2text undetected-chromedriver selenium
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Function to run the RSS crawler
run_rss_crawler() {
    log "INFO" "Running RSS crawler..."
    
    # Check if script exists
    if [ ! -f "rss_cryptonews_crawler.py" ]; then
        log "ERROR" "RSS crawler script not found: rss_cryptonews_crawler.py"
        return 1
    fi
    
    log "INFO" "Parameters: --output-dir $OUTPUT_DIR --max-articles $MAX_ARTICLES --max-feeds $MAX_FEEDS $DEBUG_MODE"
    
    python rss_cryptonews_crawler.py \
        --output-dir "$OUTPUT_DIR" \
        --max-articles "$MAX_ARTICLES" \
        --max-feeds "$MAX_FEEDS" \
        $DEBUG_MODE
        
    if [ $? -ne 0 ]; then
        log "ERROR" "RSS crawler failed"
        return 1
    fi
    
    return 0
}

# Function to run the Selenium crawler
run_selenium_crawler() {
    log "INFO" "Running Selenium crawler..."
    
    # Check if script exists
    if [ -f "cryptonews_selenium_crawler.py" ]; then
        CRAWLER_SCRIPT="cryptonews_selenium_crawler.py"
    elif [ -f "cryptonews_crawler.py" ]; then
        CRAWLER_SCRIPT="cryptonews_crawler.py"
        log "WARN" "Using older crawler script: cryptonews_crawler.py"
    else
        log "ERROR" "Selenium crawler script not found"
        return 1
    fi
    
    if [ "$HEADLESS" = true ]; then
        log "INFO" "Running in headless mode..."
    else
        log "INFO" "Running with visible browser..."
    fi
    
    log "INFO" "Parameters: --output-dir $OUTPUT_DIR --max-articles $MAX_ARTICLES --max-sections $MAX_SECTIONS --max-retries $MAX_RETRIES $VISIBLE_BROWSER $DEBUG_MODE"
    
    python $CRAWLER_SCRIPT \
        --output-dir "$OUTPUT_DIR" \
        --max-articles "$MAX_ARTICLES" \
        --max-sections "$MAX_SECTIONS" \
        --max-retries "$MAX_RETRIES" \
        $VISIBLE_BROWSER \
        $DEBUG_MODE
        
    if [ $? -ne 0 ]; then
        log "ERROR" "Selenium crawler failed"
        return 1
    fi
    
    # Optional: Run article cleaning pipeline if it exists
    if [ -f "clean_article_content.py" ]; then
        log "INFO" "Running article cleaning pipeline..."
        python clean_article_content.py \
            --input-dir "$OUTPUT_DIR" \
            --output-dir "${OUTPUT_DIR}_clean"
    fi
    
    return 0
}

# Main execution
log "INFO" "Starting CryptoNews.com crawler (Type: $CRAWLER_TYPE)"
log "INFO" "Output directory: $OUTPUT_DIR"

# Track execution time
START_TIME=$(date +%s)

success=false
if [ "$CRAWLER_TYPE" = "rss" ]; then
    run_rss_crawler
    if [ $? -eq 0 ]; then
        success=true
    fi
else
    run_selenium_crawler
    if [ $? -eq 0 ]; then
        success=true
    fi
fi

# Calculate execution time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

# Deactivate virtual environment
log "INFO" "Deactivating virtual environment..."
deactivate

# Final status
if [ "$success" = true ]; then
    log "INFO" "Crawling completed successfully in ${MINUTES}m ${SECONDS}s!"
    log "INFO" "Results saved in: $OUTPUT_DIR"
    exit 0
else
    log "ERROR" "Crawling process failed after ${MINUTES}m ${SECONDS}s."
    exit 1
fi 