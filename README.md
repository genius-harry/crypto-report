# BeInCrypto Crawler

A Python-based crawler for BeInCrypto that uses RSS feeds to fetch cryptocurrency news articles.

## Features

- Fetches articles from BeInCrypto's RSS feed
- Extracts content and metadata (title, author, date, categories, featured image)
- Saves articles in both markdown and JSON formats
- Detailed logging and error handling
- Rate limiting to avoid overloading the server
- Command-line options for customization

## Requirements

- Python 3.6+
- Virtual environment (created automatically by the script)
- Required packages (installed automatically):
  - feedparser
  - requests
  - beautifulsoup4
  - html2text

## Setup

1. Clone the repository or download the files
2. Navigate to the project directory
3. Make the run script executable:

```bash
chmod +x run_beincrypto.sh
```

## Usage

Run the crawler using the provided shell script:

```bash
./run_beincrypto.sh
```

### Command Line Options

- `-a, --articles NUM`: Maximum number of articles to fetch (default: 10)
- `-o, --output DIR`: Output directory for scraped data (default: scraped_data)
- `-h, --help`: Display help message and exit

Examples:

```bash
# Fetch 5 articles
./run_beincrypto.sh -a 5

# Specify a custom output directory
./run_beincrypto.sh -o custom_data

# Fetch 20 articles and save to a custom directory
./run_beincrypto.sh -a 20 -o custom_data
```

## Output Structure

Articles are saved in a timestamped directory within the output directory. For each article, two files are created:

1. Markdown file (`.md`): Human-readable format with article content
2. JSON file (`.json`): Machine-readable format with all extracted data

Additionally, a `summary.json` file is created with statistics about the crawling process, and a `crawler_log.txt` file contains detailed logs.

## Article Format

### Markdown Format

The markdown file includes:
- Title (as heading)
- Author
- Publication date
- Categories
- Featured image (if available)
- Article content in markdown format
- Source URL

### JSON Format

The JSON file includes all extracted data:
- title
- url
- date_published
- author
- categories
- summary
- content_html (raw HTML)
- content_markdown (converted to markdown)
- featured_image (URL, if available)

## License

MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. 