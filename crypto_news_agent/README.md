# Crypto News GraphRAG System

A comprehensive system for tracking, analyzing, and generating insights about cryptocurrency news using a Graph-based Retrieval Augmented Generation (GraphRAG) approach.

## Features

1. **Search**: Automatically search for cryptocurrency news
2. **Rank**: Use AI to rank the most relevant news articles
3. **Scrape**: Extract content from news articles
4. **Graph**: Build a knowledge graph from the scraped content
5. **Report**: Generate comprehensive reports based on the knowledge graph
6. **Web Interface**: Interact with the system through a web interface

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

The system requires several API keys and configuration parameters to work properly. Copy the `.env.example` file to a new file named `.env`:

```bash
cp .env.example .env
```

Then edit the `.env` file and add your API keys and configuration:

```
# API Keys
SERP_API_KEY=your_serpapi_key_here
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here
FIRECRAWL_API_KEY=your_firecrawl_key_here

# Neo4j Credentials
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password_here
```

### 3. Configure Neo4j

Make sure Neo4j is installed and running. You can use:
- A local Neo4j instance (default URI: bolt://localhost:7687)
- A Neo4j AuraDB cloud instance
- A Neo4j Docker container

## Usage

### Run the full pipeline

```bash
python main.py
```

### Run specific phases

```bash
# Only search for news
python main.py --only-search

# Only rank articles
python main.py --only-rank

# Only scrape articles
python main.py --only-scrape

# Only build graph
python main.py --only-graph

# Only generate report
python main.py --only-report

# Only start web interface
python main.py --only-web
```

### Skip specific phases

```bash
# Skip graph building
python main.py --skip-graph

# Skip web interface
python main.py --skip-web
```

### Additional options

```bash
# Force new search
python main.py --search

# Clean database before import
python main.py --clean

# Set search query
python main.py --query "bitcoin ethereum news"

# Set number of articles to process
python main.py --limit 20

# Enable verbose output
python main.py --verbose
```

## Troubleshooting

### Report Generation Fails

If you see the error:

```
Error setting up GraphRAG: Did not find username, please add an environment variable NEO4J_USERNAME
```

Make sure you've properly set up the Neo4j credentials in your `.env` file:

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password_here
```

And ensure your Neo4j database is running and accessible.

### Chat Interface Not Working

If the chat interface in the web UI isn't responding, check that:
1. Neo4j credentials are correctly set
2. Neo4j is running and accessible
3. The knowledge graph has been populated (run with `--only-graph` first)

## License

This project is licensed under the MIT License. 