# Custom Web Crawler for Crypto News

A collection of web crawlers designed to extract and scrape news articles from cryptocurrency-focused websites. These scrapers operate without API limitations and can be customized based on site structures.

## Crawlers Available

### Basic Article Crawler (`bs_crawler.py`)
- Simple web scraper for individual articles
- Extracts metadata (title, author, date, description)
- Converts article content to markdown
- Non-JavaScript dependent (using Beautiful Soup)

### Subpage Crawler (`bs_subpage_crawler.py`)
- Extracts multiple articles from news sites
- Follows links on the homepage to scrape individual articles
- Supports different site structures (CoinDesk, Crypto.news)
- Saves articles in a site-specific directory with timestamp

### Enhanced JavaScript Crawler (`selenium_crawler.py`)
- Handles JavaScript-rendered websites
- Uses Selenium WebDriver for full browser rendering
- Special handling for dynamic content loading
- Recommended for sites like CoinDesk where content is loaded via JavaScript

### Enhanced Subpage Crawler (`enhanced_subpage_crawler.py`)
- Combines Beautiful Soup and Selenium capabilities
- Intelligently selects the best scraping method based on the site
- Improved content extraction with multiple fallback methods
- Better handling of site-specific article patterns and structures
- Can be forced to use Selenium for any site with `--force-selenium` flag

### Universal Crawler Wrapper (`crawl.py`) ✨
- **NEW!** Unified interface for all crawler types
- Automatically selects the appropriate crawler based on the URL
- Supports single articles and multi-article crawling
- Simplifies usage with consistent command-line arguments
- Includes built-in site configuration database

## Installation

```bash
# Basic requirements
pip install beautifulsoup4 requests html2text python-dateutil

# For enhanced JavaScript support (recommended)
pip install selenium webdriver-manager
```

## Usage

### Universal Crawler (Recommended)
```bash
# List supported sites and their configurations
python crawl.py --list-sites

# Crawl any URL (automatically selects appropriate crawler)
python crawl.py --url https://www.coindesk.com/ --max 5 --output-dir articles

# Force using Selenium for any site
python crawl.py --url https://crypto.news/ --force-selenium --output-dir articles
```

### Basic Article Scraper
```bash
python bs_crawler.py https://crypto.news/news/some-article-url/
```

### Subpage Crawler
```bash
python bs_subpage_crawler.py https://www.coindesk.com/ --max 5
```

### Enhanced JavaScript Crawler
```bash
python selenium_crawler.py https://www.coindesk.com/business/2025/03/31/ai-infused-blockchain-ambient-to-replace-bitcoin-says-co-founder/
```

### Enhanced Subpage Crawler
```bash
# Auto-detect best method 
python enhanced_subpage_crawler.py https://www.coindesk.com/ --max 5

# Force using Selenium for any site
python enhanced_subpage_crawler.py https://crypto.news/ --max 3 --force-selenium

# Specify custom output directory
python enhanced_subpage_crawler.py https://www.coindesk.com/ --output-dir ./my_articles
```

## Supported Sites

The crawler has been tested and configured for:

- **CoinDesk.com** - JavaScript-heavy site (uses Selenium by default)
- **Crypto.news** - Standard HTML structure (uses Beautiful Soup by default)

## Output Format

Articles are saved in markdown format with the following structure:

```markdown
# Article Title

Source: https://original-url.com/article-path
Date: 2025-03-31
Author: Author Name
Description: Brief description of the article
Image: https://path-to-featured-image.jpg
Source: domain.com
Scraped_at: 2025-04-01T15:52:10.768486

Article content in markdown format...
```

## Benefits Over Firecrawl

- No API limits or quota restrictions
- Fully customizable for specific site structures
- No third-party dependency for crawling
- Privacy (no data sharing with external APIs)
- Can handle JavaScript-rendered content
- Intelligent crawler selection for optimal results

## Limitations

- Requires maintenance as website structures change
- May encounter CAPTCHA or rate limiting for aggressive scraping
- Quality of content extraction depends on site structure
- Selenium requires ChromeDriver installation

## Future Improvements

- Proxy support for IP rotation
- Enhanced error handling and retries
- Support for more cryptocurrency news sites
- Chrome extension for one-click article scraping
- Integration with NLP for content analysis

## Using in an Existing Pipeline

The crawlers can be easily integrated into an existing data pipeline:

```python
# Using the unified crawler programmatically
from crawl import run_crawler

# Run the best crawler for a given URL
run_crawler("https://www.coindesk.com/markets/2025/03/31/bitcoin-price-article", 
            output_dir="output_dir",
            max_articles=5)

# Or import specific crawlers for more control
from enhanced_subpage_crawler import scrape_article

# Scrape a single article
result = scrape_article("https://www.coindesk.com/markets/2025/03/31/bitcoin-price-article", "output_dir")

# Access the markdown content
with open(result["output_file"], "r") as f:
    markdown_content = f.read()
    
# Process the content further...
```

## Contributing

Feel free to contribute additional site configurations by adding to the `SITE_CONFIGS` dictionary in `enhanced_subpage_crawler.py` or `crawl.py`. 