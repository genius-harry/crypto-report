#!/bin/bash
# Extract article data from all scraped directories

# Set output directory
OUTPUT_DIR="./extracted_data"
mkdir -p "$OUTPUT_DIR"

# Find all scraped directories
SCRAPED_DIRS=$(find scraped_data -mindepth 1 -maxdepth 1 -type d | sort)

echo "Found $(echo "$SCRAPED_DIRS" | wc -l | tr -d ' ') scraped directories"

# Initialize counters
TOTAL_ARTICLES=0

# Process each directory
for dir in $SCRAPED_DIRS; do
    dir_name=$(basename "$dir")
    echo "Processing $dir..."
    
    # Create output filename
    output_file="$OUTPUT_DIR/${dir_name}_articles.json"
    
    # Run extraction script
    python extract_article_data.py "$dir" --format json --output "$output_file"
    
    # Count articles in this directory
    ARTICLE_COUNT=$(grep -o '"count":' "$output_file" | head -1 | tr -d ' ' | cut -d':' -f2)
    TOTAL_ARTICLES=$((TOTAL_ARTICLES + ARTICLE_COUNT))
    
    echo "Found $ARTICLE_COUNT articles"
    echo "Saved to $output_file"
    echo "-----------------------------------------"
done

echo "All done! Extracted $TOTAL_ARTICLES articles from all directories"
echo "Data saved to $OUTPUT_DIR" 