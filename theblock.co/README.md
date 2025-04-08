# The Block Crawler

A Python-based crawler for [The Block](https://www.theblock.co/) cryptocurrency news website that uses Selenium to scrape articles and save them in markdown and JSON formats.

## Features

- Fetches articles from different categories (latest, bitcoin, ethereum, defi, business, policy)
- Extracts article content, title, publication date, author, and categories
- Saves articles in both markdown and JSON formats
- Handles Cloudflare protection using Selenium
- Includes error handling for network issues and parsing errors
- Respects rate limits to avoid overloading the server

## Requirements

- Python 3.6+
- Virtual environment (will be created automatically)
- Google Chrome browser
- Required Python packages (installed automatically):
  - selenium
  - requests
  - beautifulsoup4
  - html2text

## Setup

1. Clone the repository or download the files
2. Navigate to the project directory
3. Make the script executable:
   ```
   chmod +x run_theblock.sh
   ```

## Usage

Run the script with default options:
```
./run_theblock.sh
```

### Command-line Options

- `-a, --articles N`: Set maximum number of articles to fetch (default: 5)
- `-c, --category TYPE`: Set category to crawl (default: latest)
  - Available categories: latest, bitcoin, ethereum, defi, business, policy
- `-o, --output DIR`: Set output directory (default: scraped_data)
- `--no-headless`: Run browser in non-headless mode (visible)
- `-h, --help`: Display help message

Examples:
```
# Fetch 10 articles from the Bitcoin category
./run_theblock.sh -a 10 -c bitcoin

# Save articles to a custom directory
./run_theblock.sh -o custom_data_dir

# Run with visible browser
./run_theblock.sh --no-headless
```

## Output Structure

Articles are saved in a timestamped directory within the specified output directory (e.g., `scraped_data/20230505_123456/`). The directory contains:

- `markdown/`: Directory containing articles in markdown format
- `json/`: Directory containing articles in JSON format
- `summary.json`: Summary of the crawl, including the number of articles processed

### Article Format

#### Markdown
Each markdown file includes:
- Title
- Publication date
- Author
- Categories
- Source with link
- Full article content

#### JSON
Each JSON file includes:
- Title
- URL
- Publication date
- Author
- Content (in markdown format)
- Categories
- Source

## Error Handling

The crawler includes robust error handling for:
- Network issues
- Timeouts
- Parsing errors
- Selenium-specific errors

## Rate Limiting

To avoid overloading the server:
- Random delays between requests (1-3 seconds)
- Longer delays between article fetches (2-5 seconds)

## Important Note

The Block website (theblock.co) uses strong Cloudflare protection that blocks automated access. The current crawler attempts to bypass this protection using Selenium with various anti-detection techniques, but may still be blocked by Cloudflare's security measures.

If you encounter errors like "Sorry, you have been blocked" or timeout issues, you might need to:

1. Run the crawler with `--no-headless` mode, which will open a visible browser window and may allow you to manually solve CAPTCHA challenges
2. Consider using a premium proxy service specifically designed to bypass Cloudflare protection
3. Respect the website's terms of service and robots.txt rules

### Error Example

When running the crawler, if you see output like this:
```
Article title: Sorry, you have been blocked
```

It means Cloudflare has detected and blocked the automated access attempt.

## License

MIT License 