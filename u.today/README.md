# U.Today Crawler

A Python-based crawler for U.Today that uses direct web scraping to fetch cryptocurrency news articles.

## Features

- Fetches cryptocurrency news articles from U.Today website
- Extracts content, title, date, and author information
- Saves articles in both markdown and JSON formats
- Handles network errors and parsing issues
- Respects website by implementing rate limiting between requests

## Requirements

- Python 3.6+
- Virtual environment (venv)
- Required packages:
  - requests
  - beautifulsoup4
  - html2text

## Setup

1. Clone the repository or navigate to the project directory
2. Make the run script executable:
   ```
   chmod +x run_simple.sh
   ```

## Usage

Run the crawler with default settings (10 articles):
```
./run_simple.sh
```

Or specify the number of articles to fetch:
```
./run_simple.sh -a 5
```

## Output

The crawler saves articles in a timestamped directory under `scraped_data/`. For each article, it creates:

- Markdown file (in the `markdown/` subdirectory)
- JSON file (in the `json/` subdirectory)
- A summary JSON file with statistics about the crawl

## Article Format

### Markdown files include:
- Title (as heading)
- Date (if available)
- Author (if available)
- Source URL
- Full article content

### JSON files include:
- Title
- Date
- Author
- URL
- Content (in markdown format)

## Troubleshooting

If you encounter issues:
1. Check your internet connection
2. Verify that the website structure hasn't changed
3. Ensure all dependencies are installed correctly

## License

MIT License 