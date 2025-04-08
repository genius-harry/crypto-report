"""
Load Real Crypto News Data to Neo4j

This script loads the actual crypto news data from the project into Neo4j
for use with the GraphRAG system.
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_openai import OpenAIEmbeddings
import re

# Load environment variables
load_dotenv()

# Neo4j connection parameters
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "Yaoyiran20061111"

# OpenAI API key for generating embeddings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Path to data directory
DATA_DIR = "data"

def connect_to_neo4j():
    """Establish connection to Neo4j database."""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        # Verify connection
        with driver.session() as session:
            result = session.run("RETURN 1 AS test")
            for record in result:
                print(f"Neo4j connection test: {record['test']}")
        print("Successfully connected to Neo4j!")
        return driver
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        return None

def setup_schema(driver):
    """Set up Neo4j schema with constraints and indexes for better performance."""
    with driver.session() as session:
        # Create constraints
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Article) REQUIRE a.url IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Cryptocurrency) REQUIRE c.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Source) REQUIRE s.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (q:Query) REQUIRE q.text IS UNIQUE")
        
        # Create indexes
        session.run("CREATE INDEX IF NOT EXISTS FOR (a:Article) ON (a.searched_at)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (a:Article) ON (a.title)")
        
        print("Neo4j schema setup complete!")

def extract_crypto_mentions(text):
    """Extract cryptocurrency mentions from text."""
    if not text:
        return []
    
    # Common cryptocurrencies to look for
    crypto_patterns = {
        'Bitcoin': ['Bitcoin', 'BTC', 'XBT'],
        'Ethereum': ['Ethereum', 'ETH', 'Ether'],
        'Ripple': ['Ripple', 'XRP'],
        'Litecoin': ['Litecoin', 'LTC'],
        'Cardano': ['Cardano', 'ADA'],
        'Solana': ['Solana', 'SOL'],
        'Dogecoin': ['Dogecoin', 'DOGE'],
        'Polkadot': ['Polkadot', 'DOT'],
        'Chainlink': ['Chainlink', 'LINK'],
        'Binance Coin': ['Binance Coin', 'BNB'],
        'Tether': ['Tether', 'USDT'],
        'USD Coin': ['USDC', 'USD Coin'],
    }
    
    found_cryptos = []
    
    for crypto_name, patterns in crypto_patterns.items():
        for pattern in patterns:
            # Search for the pattern with word boundaries
            if re.search(r'\b' + re.escape(pattern) + r'\b', text, re.IGNORECASE):
                found_cryptos.append({
                    'name': crypto_name,
                    'symbol': patterns[1] if len(patterns) > 1 else patterns[0],
                    'pattern_matched': pattern
                })
                break  # Only add each crypto once
    
    return found_cryptos

def load_news_data():
    """Load crypto news data from JSON files."""
    data_files = []
    for filename in os.listdir(DATA_DIR):
        if filename.startswith('merged_results_') and filename.endswith('.json'):
            file_path = os.path.join(DATA_DIR, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    timestamp = filename.split('_')[2].split('.')[0]
                    data_files.append({
                        'timestamp': timestamp,
                        'data': data
                    })
                    print(f"Loaded {file_path}")
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
    
    # Sort by timestamp (newest first)
    data_files.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Take the newest file only
    if data_files:
        newest_data = data_files[0]['data']
        print(f"Using newest data file with timestamp {data_files[0]['timestamp']}")
        return newest_data['articles'] if 'articles' in newest_data else []
    
    return []

def process_articles(articles):
    """Process articles and prepare for Neo4j import."""
    processed_articles = []
    
    for article in articles:
        # Skip items without required fields
        if not article.get('title') or not article.get('url'):
            continue
        
        # Extract crypto mentions from title and snippet
        combined_text = f"{article.get('title', '')} {article.get('snippet', '')}"
        crypto_mentions = extract_crypto_mentions(combined_text)
        
        # Clean and standardize data
        processed_article = {
            'title': article.get('title', '').strip(),
            'url': article.get('url', '').strip(),
            'snippet': article.get('snippet', '').strip(),
            'source': article.get('source', '').strip(),
            'published_date': article.get('published_date', ''),
            'searched_at': article.get('searched_at', ''),
            'query': article.get('query', '').strip(),
            'search_engine': article.get('search_engine', '').strip(),
            'crypto_mentions': crypto_mentions
        }
        
        processed_articles.append(processed_article)
    
    return processed_articles

def import_to_neo4j(driver, articles):
    """Import processed articles into Neo4j."""
    print(f"Importing {len(articles)} articles to Neo4j...")
    
    # Import in batches
    batch_size = 25
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i+batch_size]
        
        with driver.session() as session:
            for article in batch:
                # Create article node
                params = {
                    'title': article['title'],
                    'url': article['url'],
                    'snippet': article['snippet'],
                    'source': article['source'],
                    'published_date': article['published_date'],
                    'searched_at': article['searched_at'],
                    'query': article['query'],
                    'search_engine': article['search_engine']
                }
                
                # Create article node
                session.run("""
                    MERGE (a:Article {url: $url})
                    ON CREATE SET 
                        a.title = $title,
                        a.snippet = $snippet,
                        a.published_date = $published_date,
                        a.searched_at = $searched_at,
                        a.search_engine = $search_engine
                    ON MATCH SET
                        a.title = $title,
                        a.snippet = $snippet
                """, params)
                
                # Create source and relationship
                if article['source']:
                    session.run("""
                        MATCH (a:Article {url: $url})
                        MERGE (s:Source {name: $source})
                        MERGE (a)-[:FROM]->(s)
                    """, {'url': article['url'], 'source': article['source']})
                
                # Create query and relationship
                if article['query']:
                    session.run("""
                        MATCH (a:Article {url: $url})
                        MERGE (q:Query {text: $query})
                        MERGE (a)-[:FOUND_BY]->(q)
                    """, {'url': article['url'], 'query': article['query']})
                
                # Create cryptocurrency nodes and relationships
                for crypto in article['crypto_mentions']:
                    session.run("""
                        MATCH (a:Article {url: $url})
                        MERGE (c:Cryptocurrency {name: $name})
                        ON CREATE SET c.symbol = $symbol
                        MERGE (a)-[:MENTIONS]->(c)
                    """, {
                        'url': article['url'], 
                        'name': crypto['name'],
                        'symbol': crypto['symbol']
                    })
        
        print(f"Imported batch {i//batch_size + 1}/{(len(articles)-1)//batch_size + 1}")
    
    print("Data import complete!")

def create_relationships(driver):
    """Create additional relationships between entities."""
    with driver.session() as session:
        # Create RELATED_TO relationships between cryptocurrencies mentioned in the same articles
        session.run("""
            MATCH (a:Article)-[:MENTIONS]->(c1:Cryptocurrency)
            MATCH (a)-[:MENTIONS]->(c2:Cryptocurrency)
            WHERE c1 <> c2
            MERGE (c1)-[r:RELATED_TO]-(c2)
            ON CREATE SET r.common_articles = 1
            ON MATCH SET r.common_articles = r.common_articles + 1
        """)
        
        # Create RELATED_QUERY relationships between queries mentioning the same cryptocurrency
        session.run("""
            MATCH (q1:Query)<-[:FOUND_BY]-(a1:Article)-[:MENTIONS]->(c:Cryptocurrency)
            MATCH (q2:Query)<-[:FOUND_BY]-(a2:Article)-[:MENTIONS]->(c)
            WHERE q1 <> q2
            MERGE (q1)-[r:RELATED_QUERY]-(q2)
            ON CREATE SET r.common_crypto = 1
            ON MATCH SET r.common_crypto = r.common_crypto + 1
        """)
        
        print("Relationships created!")

def run_analytics(driver):
    """Run analytics queries on the graph."""
    with driver.session() as session:
        # Count nodes by type
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] as type, count(*) as count
            ORDER BY count DESC
        """)
        print("\nNode counts:")
        for record in result:
            print(f"  {record['type']}: {record['count']}")
        
        # Find top mentioned cryptocurrencies
        result = session.run("""
            MATCH (c:Cryptocurrency)<-[r:MENTIONS]-(a:Article)
            RETURN c.name as name, c.symbol as symbol, count(r) as mentions
            ORDER BY mentions DESC
            LIMIT 10
        """)
        print("\nTop mentioned cryptocurrencies:")
        for record in result:
            print(f"  {record['name']} ({record['symbol']}): {record['mentions']} mentions")
        
        # Find top sources
        result = session.run("""
            MATCH (s:Source)<-[r:FROM]-(a:Article)
            RETURN s.name as source, count(r) as articles
            ORDER BY articles DESC
            LIMIT 5
        """)
        print("\nTop sources:")
        for record in result:
            print(f"  {record['source']}: {record['articles']} articles")
        
        # Find strongest crypto relationships
        result = session.run("""
            MATCH (c1:Cryptocurrency)-[r:RELATED_TO]-(c2:Cryptocurrency)
            RETURN c1.name as crypto1, c2.name as crypto2, r.common_articles as strength
            ORDER BY strength DESC
            LIMIT 5
        """)
        print("\nStrongest cryptocurrency relationships:")
        for record in result:
            print(f"  {record['crypto1']} - {record['crypto2']}: mentioned together in {record['strength']} articles")

def main():
    """Main function to load real crypto news data to Neo4j."""
    print("Loading Real Crypto News Data to Neo4j")
    print("=====================================\n")
    
    # Connect to Neo4j
    driver = connect_to_neo4j()
    if not driver:
        print("Failed to connect to Neo4j. Please make sure Neo4j is running with the correct credentials.")
        return
    
    # Set up Neo4j schema
    setup_schema(driver)
    
    # Load news data
    articles = load_news_data()
    if not articles:
        print("No news data found!")
        driver.close()
        return
    
    # Process articles
    processed_articles = process_articles(articles)
    print(f"Processed {len(processed_articles)} articles")
    
    # Import to Neo4j
    import_to_neo4j(driver, processed_articles)
    
    # Create relationships
    create_relationships(driver)
    
    # Run analytics
    run_analytics(driver)
    
    # Close connection
    driver.close()
    print("\nNeo4j connection closed.")

if __name__ == "__main__":
    main() 