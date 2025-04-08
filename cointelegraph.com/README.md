# Cointelegraph.com Crawler

A Python-based crawler for Cointelegraph.com that uses RSS feeds to avoid Cloudflare protection.

## Features

- Fetches articles from Cointelegraph's main RSS feed
- Extracts article content, metadata, and formatting
- Saves articles in both markdown and JSON formats
- Handles errors gracefully
- Respects rate limits to avoid overwhelming the server

## Requirements

- Python 3.8+
- Virtual environment (venv)
- Required packages (installed automatically):
  - feedparser
  - requests
  - beautifulsoup4
  - html2text

## Setup

1. Clone the repository
2. Navigate to the project directory:
   ```bash
   cd cointelegraph.com
   ```
3. The `run_cointelegraph.sh` script will automatically:
   - Create a virtual environment
   - Install required packages
   - Run the crawler

## Usage

Run the crawler using the shell script:

```bash
./run_cointelegraph.sh [options]
```

Options:
- `-a, --max-articles N`: Maximum number of articles to fetch (default: 5)
- `-f, --max-feeds N`: Maximum number of feeds to process (default: 1)

Example:
```bash
./run_cointelegraph.sh -a 10  # Fetch 10 articles
```

## Output

The crawler saves articles in a timestamped directory under `scraped_data/`:

```
scraped_data/YYYYMMDD_HHMMSS/
├── article_title_1.md         # Markdown version
├── article_title_1.json       # JSON version with metadata
├── article_title_2.md
├── article_title_2.json
└── summary.json              # Summary of the crawling session
```

### Article Format

Each article is saved in two formats:

1. Markdown (`.md`):
   - Title
   - Date
   - Author
   - URL
   - Content in clean markdown format

2. JSON (`.json`):
   - All metadata
   - Raw HTML content
   - Markdown content
   - Success status

## Error Handling

The crawler includes robust error handling for:
- Network issues
- Invalid RSS feeds
- Cloudflare protection
- Rate limiting
- Invalid article content

## Rate Limiting

To avoid overwhelming the server:
- Random delays between requests (2-5 seconds)
- Browser-like headers
- Session reuse
- Proper error handling and backoff

## License

MIT License 