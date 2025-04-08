# CoinDesk Article Extraction & Cleaning

This folder contains scripts for extracting and cleaning articles from CoinDesk.com.

## Scripts

1. **coindesk_crawler.py**: A custom crawler that uses Selenium to scrape articles from CoinDesk's website, handling JavaScript rendering and extracting content.

2. **extract_article_data.py**: Extracts title, author, content, and metadata from the scraped markdown files.

3. **clean_article_content.py**: Cleans up article content by removing navigation elements, ads, and other non-essential content, providing cleaner text for analysis.

## Usage

### Running the Crawler

```bash
python coindesk_crawler.py --max-articles 10 --max-sections 5 --output-dir scraped_data
```

### Extracting Article Data

```bash
python extract_article_data.py scraped_data/DIRECTORY_NAME --format json --output output_file.json
```

or

```bash
python extract_article_data.py scraped_data/DIRECTORY_NAME --format summary
```

### Cleaning Article Content

```bash
python clean_article_content.py scraped_data/DIRECTORY_NAME --format text --output-dir clean_articles
```

or

```bash
python clean_article_content.py scraped_data/DIRECTORY_NAME --format json --output-dir clean_articles_json
```

## Output Structure

- `scraped_data/`: Contains the raw scraped articles in markdown format organized by timestamp-based directories
- `clean_articles/`: Contains cleaned article text files with non-essential content removed
- `extracted_data/`: Contains JSON files with extracted metadata and content

## Example Workflow

1. Scrape articles from CoinDesk
   ```bash
   python coindesk_crawler.py --max-articles 20 --max-sections 5 --output-dir scraped_data
   ```

2. Extract data from the scraped articles
   ```bash
   python extract_article_data.py scraped_data/coindesk_YYYYMMDD_HHMMSS --format json --output extracted_data.json
   ```

3. Clean the article content for better readability
   ```bash
   python clean_article_content.py scraped_data/coindesk_YYYYMMDD_HHMMSS --format text --output-dir clean_articles
   ```

4. Process all scraped directories at once
   ```bash
   ./extract_all_articles.sh
   ```

## Cleaning Process

The article cleaning process:

1. Removes cryptocurrency price ticker sections
2. Removes navigation elements and advertisement sections
3. Removes video player sections and newsletter signup forms
4. Removes footer sections and author bio sections
5. Removes tags and image links with minimal text
6. Cleans up multiple newlines and other formatting issues 