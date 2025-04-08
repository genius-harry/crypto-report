# Bitcoin.com News RSS Crawler

A Python-based crawler that fetches cryptocurrency news articles from [Bitcoin.com News](https://news.bitcoin.com/) using their RSS feed.

## Overview

This crawler leverages the RSS feed provided by Bitcoin.com to extract the latest cryptocurrency news. It allows you to fetch a specified number of articles, process them, and save them in both Markdown and JSON formats with rich metadata.

## Important Note

Bitcoin.com is a JavaScript-based Single Page Application (SPA) where article content is loaded dynamically after the page loads. This makes direct content extraction from HTML responses challenging.

Our solution:
- We primarily rely on the RSS feed data which contains article summaries
- When article content can't be extracted from HTML, we use the RSS description as the content
- The crawler adds a note in the output indicating when full content couldn't be retrieved

## Features

- RSS feed-based article extraction for reliable and efficient crawling
- Fetch cryptocurrency news articles with full content and metadata
- Smart fallback to RSS summary when full content can't be extracted
- Extract article titles, URLs, publication dates, authors, categories, and thumbnail images
- Save articles in both Markdown and JSON formats
- Process articles with proper error handling and retry mechanisms
- Implement random delays to respect website rate limits
- Command-line interface for customizing crawling parameters

## Requirements

- Python 3.6+
- Virtual environment (automatically created by the run script)
- Required packages (automatically installed by the run script):
  - requests
  - beautifulsoup4
  - html2text
  - feedparser

## Setup

1. Navigate to the project directory
2. Make the run script executable:
   ```
   chmod +x run_bitcoincom_rss.sh
   ```

## Usage

Run the crawler using the provided shell script:

```bash
./run_bitcoincom_rss.sh
```

### Command-line Options

- `-a, --articles N`: Set the maximum number of articles to fetch per feed (default: 10)
- `-f, --feeds N`: Set the maximum number of feeds to process (default: all available)
- `-o, --output DIR`: Set the output directory (default: scraped_data)
- `-h, --help`: Display help message

Examples:

```bash
# Fetch 5 articles from the RSS feed
./run_bitcoincom_rss.sh -a 5

# Fetch 3 articles and save to custom directory
./run_bitcoincom_rss.sh -a 3 -o custom_data
```

## Output Structure

Articles are saved in a timestamped directory (format: YYYYMMDD_HHMMSS) within the specified output directory. Each article is saved in two formats:

1. **Markdown (.md)**: Human-readable article with metadata
2. **JSON (.json)**: Structured data with all article metadata

## Article Format

### Markdown Format

Each Markdown file includes:
- Article title as heading
- Source URL
- Publication date
- Author name
- Categories (if available)
- Thumbnail image (if available)
- Summary section (if available)
- Full article content converted from HTML to Markdown (or RSS summary if full content unavailable)

### JSON Format

Each JSON file contains a structured representation of the article with all available metadata:
- title
- url
- publication_date
- author
- content (Markdown)
- html_content (original HTML)
- summary
- meta_description
- categories
- thumbnail_url
- filename

## Error Handling

The crawler includes robust error handling for:
- Network connection issues
- RSS feed parsing failures
- Article content extraction problems
- HTML to Markdown conversion errors
- File I/O operations
- JavaScript-based SPA content loading

## Rate Limiting

To be a good web citizen and avoid overwhelming the server, the crawler implements random delays between requests.

## License

MIT License 