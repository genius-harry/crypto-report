"""
Load Crypto News Data to Neo4j

This script demonstrates how to load and structure crypto news data into Neo4j
for use with a GraphRAG system.
"""

import os
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_openai import OpenAIEmbeddings

# Load environment variables
load_dotenv()

# Neo4j connection parameters - update these after installing Neo4j Desktop
NEO4J_URI = "bolt://localhost:7687"  # Default Neo4j URI
NEO4J_USERNAME = "neo4j"             # Default username
NEO4J_PASSWORD = "Yaoyiran20061111"  # Updated password

# OpenAI API key for generating embeddings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Paths
DATA_DIR = "data"  # Path to your crypto news data

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
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Article) REQUIRE a.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Cryptocurrency) REQUIRE c.symbol IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Source) REQUIRE s.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE")
        
        # Create indexes
        session.run("CREATE INDEX IF NOT EXISTS FOR (a:Article) ON (a.date)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (a:Article) ON (a.title)")
        
        print("Neo4j schema setup complete!")

def load_json_files(directory):
    """Load JSON files from directory into a list of dictionaries."""
    data = []
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    file_data = json.load(file)
                    if isinstance(file_data, list):
                        data.extend(file_data)
                    else:
                        data.append(file_data)
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
    return data

def generate_embeddings(text_list):
    """Generate embeddings for a list of texts using OpenAI."""
    embeddings = OpenAIEmbeddings()
    return embeddings.embed_documents(text_list)

def process_article_data(news_data):
    """Process and clean news data for Neo4j import."""
    processed_data = []
    
    for item in news_data:
        # Skip items without required fields
        if not item.get('title') or not item.get('content'):
            continue
            
        # Clean and standardize data
        article = {
            'id': item.get('id', hash(item.get('title', '') + str(item.get('date', '')))),
            'title': item.get('title', '').strip(),
            'content': item.get('content', '').strip(),
            'summary': item.get('summary', '').strip() if item.get('summary') else '',
            'date': item.get('date', ''),
            'source': item.get('source', '').strip() if item.get('source') else 'Unknown',
            'url': item.get('url', '').strip() if item.get('url') else '',
            'topics': item.get('topics', []),
            'sentiment': item.get('sentiment', 0),
            'cryptocurrencies': []
        }
        
        # Extract cryptocurrency mentions
        if 'entities' in item and isinstance(item['entities'], list):
            # Extract crypto entities
            for entity in item['entities']:
                if entity.get('type') == 'cryptocurrency':
                    article['cryptocurrencies'].append({
                        'name': entity.get('name', '').strip(),
                        'symbol': entity.get('symbol', '').strip().upper(),
                        'confidence': entity.get('confidence', 1.0)
                    })
        
        processed_data.append(article)
    
    return processed_data

def import_to_neo4j(driver, processed_data):
    """Import processed news data into Neo4j."""
    print(f"Importing {len(processed_data)} articles to Neo4j...")
    
    # Generate embeddings for article content
    article_contents = [article['content'] for article in processed_data]
    if article_contents:
        try:
            print("Generating embeddings for articles...")
            embeddings = generate_embeddings(article_contents)
            
            # Add embeddings to articles
            for i, article in enumerate(processed_data):
                article['embedding'] = embeddings[i]
                
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            # Continue without embeddings
            for article in processed_data:
                article['embedding'] = []
    
    # Import in batches
    batch_size = 50
    for i in range(0, len(processed_data), batch_size):
        batch = processed_data[i:i+batch_size]
        
        with driver.session() as session:
            for article in batch:
                # Create article node
                article_id = article['id']
                
                # Using Cypher parameters to prevent injection
                params = {
                    'id': article_id,
                    'title': article['title'],
                    'content': article['content'],
                    'summary': article['summary'],
                    'date': article['date'],
                    'url': article['url'],
                    'sentiment': article['sentiment'],
                    'embedding': article['embedding']
                }
                
                # Create article node with embedding
                session.run("""
                    CREATE (a:Article {
                        id: $id,
                        title: $title,
                        content: $content,
                        summary: $summary,
                        date: $date,
                        url: $url,
                        sentiment: $sentiment
                    })
                """, params)
                
                # If using Neo4j 5.0+ with vector capabilities, add embedding
                if article['embedding']:
                    session.run("""
                        MATCH (a:Article {id: $id})
                        CALL db.create.setNodeVectorProperty(a, 'embedding', $embedding)
                        YIELD node
                        RETURN node
                    """, {'id': article_id, 'embedding': article['embedding']})
                
                # Create source and relationship
                session.run("""
                    MATCH (a:Article {id: $id})
                    MERGE (s:Source {name: $source})
                    CREATE (a)-[:FROM]->(s)
                """, {'id': article_id, 'source': article['source']})
                
                # Create topic nodes and relationships
                for topic in article['topics']:
                    if topic:
                        session.run("""
                            MATCH (a:Article {id: $id})
                            MERGE (t:Topic {name: $topic})
                            CREATE (a)-[:ABOUT]->(t)
                        """, {'id': article_id, 'topic': topic})
                
                # Create cryptocurrency nodes and relationships
                for crypto in article['cryptocurrencies']:
                    if crypto['symbol']:
                        session.run("""
                            MATCH (a:Article {id: $id})
                            MERGE (c:Cryptocurrency {symbol: $symbol})
                            ON CREATE SET c.name = $name
                            CREATE (a)-[:MENTIONS {confidence: $confidence}]->(c)
                        """, {
                            'id': article_id, 
                            'symbol': crypto['symbol'],
                            'name': crypto['name'],
                            'confidence': crypto['confidence']
                        })
        
        print(f"Imported batch {i//batch_size + 1}/{(len(processed_data)-1)//batch_size + 1}")
    
    print("Data import complete!")

def create_vector_index(driver):
    """Create a vector index for article embeddings if using Neo4j 5.0+."""
    try:
        with driver.session() as session:
            # Check if vector indexing is available
            result = session.run("""
                CALL dbms.procedures() 
                YIELD name 
                WHERE name = 'db.index.vector.createNodeIndex' 
                RETURN count(*) > 0 AS hasVectorIndex
            """)
            has_vector = result.single()["hasVectorIndex"]
            
            if has_vector:
                # Create vector index
                session.run("""
                    CALL db.index.vector.createNodeIndex(
                        'articleEmbeddings',
                        'Article',
                        'embedding',
                        1536,  // OpenAI embedding dimensions
                        'cosine'
                    )
                """)
                print("Vector index created for article embeddings!")
            else:
                print("Vector indexing not available in this Neo4j version.")
    except Exception as e:
        print(f"Error creating vector index: {e}")

def main():
    """Main function to load crypto data to Neo4j."""
    print("Crypto News Data to Neo4j Loader")
    print("================================\n")
    
    # Connect to Neo4j
    driver = connect_to_neo4j()
    if not driver:
        print("Failed to connect to Neo4j. Please make sure Neo4j is running with the correct credentials.")
        return
    
    # Set up Neo4j schema
    setup_schema(driver)
    
    # Data directory path
    data_dir = DATA_DIR
    if not os.path.exists(data_dir):
        print(f"Data directory {data_dir} not found!")
        driver.close()
        return
    
    # Load JSON data
    print(f"Loading data from {data_dir}...")
    news_data = load_json_files(data_dir)
    print(f"Loaded {len(news_data)} items")
    
    if not news_data:
        print("No data found to import!")
        driver.close()
        return
    
    # Process data
    processed_data = process_article_data(news_data)
    print(f"Processed {len(processed_data)} articles")
    
    # Import to Neo4j
    import_to_neo4j(driver, processed_data)
    
    # Create vector index for similarity search
    create_vector_index(driver)
    
    # Close connection
    driver.close()
    print("\nNeo4j connection closed.")
    print("Data loading complete!")

if __name__ == "__main__":
    main() 