# CryptoNews.com Crawler

A robust crawler for [CryptoNews.com](https://cryptonews.com/) that extracts cryptocurrency news articles, reports, and analyses. This crawler supports both RSS feed-based crawling and Selenium-based web scraping to bypass Cloudflare protection.

## Features

- **Dual Crawling Approaches**:
  - RSS Feed Crawler: Uses the site's RSS feeds to extract recent articles
  - Selenium Web Crawler: Uses browser automation to bypass Cloudflare protection
  
- **Article Extraction**:
  - Extracts full article content, titles, dates, authors, and tags
  - Special handling for different article types (news, reports, external content)
  - Saves articles in both Markdown and JSON formats
  
- **Robust Error Handling**:
  - Automatic retries for failed requests
  - Handles Cloudflare protection
  - Detailed logging for troubleshooting
  
- **Rate Limiting & Respect**:
  - Random delays between requests
  - User-agent rotation and browser fingerprint avoidance
  
- **Configurable Options**:
  - Set maximum articles to crawl
  - Choose sections to crawl
  - Specify output directory
  - Run with visible or headless browser

## Requirements

- Python 3.8+
- Virtual environment (recommended)
- Required packages:
  - beautifulsoup4
  - feedparser
  - html2text
  - requests
  - undetected-chromedriver
  - selenium

## Installation

1. Clone the repository
2. Navigate to the project directory
3. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   ```
4. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
5. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Using the Run Script

The easiest way to run the crawler is with the run script:

```bash
# Make the script executable
chmod +x run_cryptonews_improved.sh

# Run with default options (Selenium crawler, 10 articles max)
./run_cryptonews_improved.sh

# Run RSS crawler with 20 articles max
./run_cryptonews_improved.sh --type rss --articles 20

# Run Selenium crawler with visible browser and debug mode
./run_cryptonews_improved.sh --type selenium --articles 5 --visible --debug
```

### Command Line Options

- `-t, --type`: Crawler type to use (`rss` or `selenium`, default: `selenium`)
- `-a, --articles`: Maximum number of articles to scrape (default: 10)
- `-f, --feeds`: Maximum number of RSS feeds to process (default: 4, RSS crawler only)
- `-s, --sections`: Maximum number of sections to scrape (default: 3, Selenium crawler only)
- `-r, --retries`: Maximum number of retries for failed requests (default: 3)
- `-o, --output`: Output directory (default: `scraped_data`)
- `-v, --visible`: Run Selenium crawler with visible browser
- `-d, --debug`: Enable debug mode for more verbose output
- `-h, --help`: Display help message

### Running Directly with Python

You can also run the crawlers directly:

```bash
# Run RSS crawler
python rss_cryptonews_crawler.py --output-dir scraped_data --max-articles 10 --max-feeds 4

# Run Selenium crawler
python cryptonews_selenium_crawler.py --output-dir scraped_data --max-articles 10 --max-sections 3 --visible
```

## Output

Articles are saved in a timestamped directory under the specified output directory:

```
scraped_data/
└── 20250408_135759/
    ├── 20250408_135810_article_title.md
    ├── 20250408_135810_article_title.json
    ├── 20250408_135824_another_article.md
    ├── 20250408_135824_another_article.json
    └── crawl_results.json
```

- Each article is saved in both Markdown (`.md`) and JSON (`.json`) format
- The Markdown file includes the article content formatted for readability
- The JSON file contains all extracted metadata and content
- `crawl_results.json` contains summary information about the crawl

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 