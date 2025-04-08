#!/bin/bash

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p data/search_results
mkdir -p data/articles
mkdir -p data/ranked
mkdir -p markdown/formatted
mkdir -p output
mkdir -p static
mkdir -p templates

# Display setup complete message
echo ""
echo "Setup complete! You can now run the Crypto News GraphRAG System:"
echo ""
echo "  ./run_graphrag.sh"
echo ""
echo "Additional options:"
echo "  --search       : Search for new crypto news"
echo "  --clean        : Clean Neo4j database before importing data"
echo "  --skip-graph   : Skip graph building (use existing data)"
echo "  --skip-web     : Skip web interface"
echo "  --model MODEL  : LLM model to use for report generation (default: gpt-4)"
echo "  --query QUERY  : Search query (default: cryptocurrency news bitcoin ethereum)"
echo "  --limit LIMIT  : Number of articles to process (default: 20)"
echo "" 