# BeInCrypto News Crawler

A web crawler for scraping cryptocurrency news articles from BeInCrypto.com.

## Features

- Scrapes latest cryptocurrency news articles from BeInCrypto.com
- Extracts article title, content, publication date, author, and categories
- Saves articles in both Markdown and JSON formats
- Includes error handling and rate limiting to avoid overwhelming the server
- Command-line options for customizing the crawling process

## Requirements

- Python 3.6+
- Required packages:
  - requests
  - beautifulsoup4
  - html2text

## Setup

1. Clone the repository
2. Navigate to the project directory
3. Run the `run_beincrypto.sh` script

## Usage

```bash
./run_beincrypto.sh [options]
```

Options:
- `-a, --articles NUMBER`: Maximum number of articles to scrape (default: 10)
- `-o, --output DIR`: Output directory for scraped articles (default: scraped_data)
- `-h, --help`: Display help message and exit

## Output

The crawler saves articles in a timestamped directory within the specified output directory. Each article is saved in two formats:

1. Markdown (`.md`) - Human-readable format with article content
2. JSON (`.json`) - Machine-readable format with all article metadata

## Example

```bash
./run_beincrypto.sh -a 5 -o my_articles
```

This command will scrape the 5 most recent articles and save them in the `my_articles` directory.

## License

MIT License 