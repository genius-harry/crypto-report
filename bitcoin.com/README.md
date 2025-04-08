# Bitcoin.com News Crawler

This repository contains three Python-based crawlers designed to fetch cryptocurrency news articles from [Bitcoin.com News](https://news.bitcoin.com/):

1. **RSS Feed Crawler**: Uses the RSS feed to extract articles
2. **Selenium-based Crawler** (Recommended): Uses Selenium WebDriver to render JavaScript and extract full article content
3. **Web Crawler**: Attempts to scrape articles directly from the website (less reliable)

## Important Note

The Bitcoin.com website is a modern JavaScript-based single-page application (SPA), which makes direct web scraping challenging. We offer three solutions:

1. **Selenium Crawler** (Recommended for full content): The `bitcoincom_selenium_crawler.py` script uses Selenium WebDriver to render the JavaScript and extract complete article content.

2. **RSS Feed Crawler** (Simpler, no dependencies): The `bitcoincom_crawler.py` script provides a lightweight option using the RSS feed but with truncated content.

3. **Web Crawler** (Least reliable): Basic scraper that attempts to extract from the static HTML.

## Features

- Three different crawling methods for different needs
- Extract article content, titles, dates, authors, and other metadata
- Save articles in both Markdown and JSON formats
- Handle network errors and parsing exceptions gracefully
- Implement random delays to respect rate limits

## Requirements

- Python 3.6+
- Virtual environment (automatically created by the run scripts)
- Required packages (automatically installed by the run scripts):
  - requests
  - beautifulsoup4
  - html2text
  - feedparser
  - selenium (for the Selenium crawler only)
- For Selenium crawler:
  - Chrome or Chromium browser
  - ChromeDriver (optional - modern Selenium versions include WebDriver Manager)

## Setup

1. Navigate to the project directory
2. Make the run scripts executable:
   ```
   chmod +x run_bitcoincom_rss.sh run_bitcoincom_selenium.sh run_master.sh
   ```

## Usage

### Master Script (Recommended)

Use the master script to choose which crawler(s) to run:

```
./run_master.sh
```

#### Command-line Options for Master Script

- `-t, --type TYPE`: Choose crawler type: web, rss, selenium, all (default: rss)
- `-a, --articles N`: Set the maximum number of articles to fetch (default: 10)
- `-c, --category TYPE`: Set the category for web crawler: news, bitcoin, ethereum, altcoins (default: news)
- `-f, --feeds N`: Set the maximum number of feeds for RSS crawler (default: 1)
- `-o, --output DIR`: Set the output directory (default: scraped_data)
- `--no-headless`: Run Selenium browser in non-headless mode (visible)
- `-h, --help`: Display help message

Examples:

```bash
# Run the Selenium crawler to get full article content (recommended)
./run_master.sh -t selenium -a 5

# Run only the RSS crawler for lightweight operation
./run_master.sh -t rss -a 5

# Run all crawlers for comparison
./run_master.sh -t all -a 3

# Run the Selenium crawler with a visible browser window
./run_master.sh -t selenium -a 2 --no-headless
```

### Individual Crawlers

You can also run the crawlers individually:

#### Selenium Crawler (Recommended for full content)

```
./run_bitcoincom_selenium.sh
```

Options:
- `-a, --articles N`: Set maximum number of articles to fetch per feed (default: 5)
- `-f, --feeds N`: Set maximum number of feeds to process (default: 1)
- `-o, --output DIR`: Set output directory (default: scraped_data)
- `--no-headless`: Run browser in non-headless mode (visible)

#### RSS Crawler (Lightweight option)

```
./run_bitcoincom_rss.sh
```

Options:
- `-a, --articles N`: Set maximum number of articles to fetch per feed (default: 10)
- `-f, --feeds N`: Set maximum number of feeds to process (default: all)
- `-o, --output DIR`: Set output directory (default: scraped_data)

#### Web Crawler (Less Reliable)

```
./run_bitcoin.sh
```

Options:
- `-a, --articles N`: Set maximum number of articles to fetch (default: 10)
- `-c, --category TYPE`: Set category to crawl: news, bitcoin, ethereum, altcoins (default: news)
- `-o, --output DIR`: Set output directory (default: scraped_data)

## Output Structure

Articles are saved in a timestamped directory (format: YYYYMMDD_HHMMSS) within the specified output directory. Each article is saved in two formats:

1. **Markdown (.md)**: Human-readable article with metadata
2. **JSON (.json)**: Structured data with all article metadata

## Comparison of Methods

| Method           | Advantages                                 | Disadvantages                               |
|------------------|--------------------------------------------|--------------------------------------------|
| Selenium Crawler | Full article content, handles JavaScript   | Requires Chrome, more dependencies          |
| RSS Crawler      | Simple, fast, reliable metadata            | Only gets truncated article content         |
| Web Crawler      | Attempts direct extraction                 | Unreliable with JavaScript-heavy sites      |

## Error Handling

All crawlers include robust error handling for:
- Network connection issues
- HTML/RSS parsing failures
- Article content extraction problems
- File I/O errors
- JavaScript-based SPA content loading

## Rate Limiting

To avoid overwhelming the server, the crawlers implement random delays between requests.

## License

MIT License 