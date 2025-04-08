#!/bin/bash
# Run script for CoinDesk crawler

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
MAX_ARTICLES=10
MAX_SECTIONS=5
OUTPUT_DIR="articles"
START_URL="https://www.coindesk.com"
TEST_MODE=false

# Display usage information
function show_usage {
    echo -e "${BLUE}CoinDesk Crawler Runner${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help                 Show this help message and exit"
    echo "  -a, --max-articles N       Maximum number of articles to scrape (default: $MAX_ARTICLES)"
    echo "  -s, --max-sections N       Maximum number of sections to visit (default: $MAX_SECTIONS)"
    echo "  -o, --output-dir DIR       Directory to save articles (default: $OUTPUT_DIR)"
    echo "  -u, --url URL              Starting URL (default: $START_URL)"
    echo "  -t, --test                 Run in test mode (limited scope)"
    echo "  --test-selenium            Test Selenium availability only"
    echo "  --test-links               Test link extraction only"
    echo "  --test-article             Test article scraping only"
    echo ""
    echo "Examples:"
    echo "  $0 --max-articles 20 --output-dir coindesk_articles"
    echo "  $0 --test"
    echo "  $0 --url https://www.coindesk.com/markets"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_usage
            exit 0
            ;;
        -a|--max-articles)
            MAX_ARTICLES="$2"
            shift 2
            ;;
        -s|--max-sections)
            MAX_SECTIONS="$2"
            shift 2
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -u|--url)
            START_URL="$2"
            shift 2
            ;;
        -t|--test)
            TEST_MODE=true
            shift
            ;;
        --test-selenium)
            python test_crawler.py --selenium-only
            exit $?
            ;;
        --test-links)
            python test_crawler.py --links-only
            exit $?
            ;;
        --test-article)
            python test_crawler.py --article-only
            exit $?
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Check if Python and required modules are available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed or not in PATH${NC}"
    exit 1
fi

# Ensure the crawler script exists
if [ ! -f "coindesk_crawler.py" ]; then
    echo -e "${RED}Error: coindesk_crawler.py not found in current directory${NC}"
    exit 1
fi

# Check if we need to run tests first
if $TEST_MODE; then
    echo -e "${YELLOW}Running crawler tests...${NC}"
    python test_crawler.py
    TEST_RESULT=$?
    
    if [ $TEST_RESULT -ne 0 ]; then
        echo -e "${RED}Tests failed. Not running crawler.${NC}"
        exit $TEST_RESULT
    fi
    
    echo -e "${GREEN}Tests passed. Proceeding with crawler...${NC}"
    # Use smaller limits for tests
    MAX_ARTICLES=3
    MAX_SECTIONS=2
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Run the crawler
echo -e "${BLUE}Starting CoinDesk crawler...${NC}"
echo "Maximum articles: $MAX_ARTICLES"
echo "Maximum sections: $MAX_SECTIONS"
echo "Output directory: $OUTPUT_DIR"
echo "Starting URL: $START_URL"
echo ""

python coindesk_crawler.py \
    --max-articles "$MAX_ARTICLES" \
    --max-sections "$MAX_SECTIONS" \
    --output-dir "$OUTPUT_DIR" \
    --start-url "$START_URL"

CRAWLER_RESULT=$?

if [ $CRAWLER_RESULT -eq 0 ]; then
    echo -e "${GREEN}Crawler completed successfully!${NC}"
else
    echo -e "${RED}Crawler encountered errors.${NC}"
fi

exit $CRAWLER_RESULT 