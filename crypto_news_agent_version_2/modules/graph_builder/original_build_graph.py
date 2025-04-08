import os
import sys
import json
from typing import Dict, List, Any, Tuple, Optional
import networkx as nx
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from neo4j import GraphDatabase
import datetime
import re

# Load environment variables
load_dotenv()

# Directory paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(CURRENT_DIR, 'static')
TEMPLATES_DIR = os.path.join(CURRENT_DIR, 'templates')
MARKDOWN_DIR = os.path.join(CURRENT_DIR, 'markdown', 'formatted')
OUTPUT_DIR = os.path.join(CURRENT_DIR, 'output')

# Ensure directories exist
for dir_path in [STATIC_DIR, TEMPLATES_DIR, OUTPUT_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Neo4j connection parameters
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "Yaoyiran20061111"

def connect_to_neo4j():
    """Connect to Neo4j database."""
    try:
        driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        
        # Test connection
        with driver.session() as session:
            result = session.run("RETURN 1 AS test")
            connection_test = result.single()["test"]
            print(f"Neo4j connection test: {connection_test}")
            print("Successfully connected to Neo4j!")
            
        return driver
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        sys.exit(1)

def setup_schema(driver):
    """Set up the Neo4j schema with constraints."""
    with driver.session() as session:
        # Create constraints for unique nodes
        session.run("""
            CREATE CONSTRAINT article_id IF NOT EXISTS 
            FOR (a:Article) REQUIRE a.id IS UNIQUE
        """)
        
        session.run("""
            CREATE CONSTRAINT cryptocurrency_name IF NOT EXISTS
            FOR (c:Cryptocurrency) REQUIRE c.name IS UNIQUE
        """)
        
        session.run("""
            CREATE CONSTRAINT source_name IF NOT EXISTS
            FOR (s:Source) REQUIRE s.name IS UNIQUE
        """)
        
        session.run("""
            CREATE CONSTRAINT person_name IF NOT EXISTS
            FOR (p:Person) REQUIRE p.name IS UNIQUE
        """)
        
        session.run("""
            CREATE CONSTRAINT topic_name IF NOT EXISTS
            FOR (t:Topic) REQUIRE t.name IS UNIQUE
        """)
    
    print("Neo4j schema setup complete!")

def create_crypto_network(driver):
    """Create a visualization of cryptocurrency relationships."""
    plt.figure(figsize=(12, 10))
    
    # Get cryptocurrency nodes and their mentions
    with driver.session() as session:
        crypto_mentions = session.run("""
            MATCH (c:Cryptocurrency)<-[:MENTIONS_CRYPTO]-(a:Article)
            RETURN c.name as name, c.symbol as symbol, count(a) as article_count
            ORDER BY article_count DESC
        """).data()
        
        crypto_relationships = session.run("""
            MATCH (c1:Cryptocurrency)<-[:MENTIONS_CRYPTO]-(a:Article)-[:MENTIONS_CRYPTO]->(c2:Cryptocurrency)
            WHERE c1.name < c2.name
            RETURN c1.name as crypto1, c2.name as crypto2, 
                   count(a) as together_count
            ORDER BY together_count DESC
            LIMIT 20
        """).data()
    
    # Create graph
    G = nx.Graph()
    
    # Add cryptocurrency nodes
    for crypto in crypto_mentions:
        # Scale node size based on number of mentions
        node_size = 500 + (crypto["article_count"] * 50)
        G.add_node(crypto["name"], size=node_size, symbol=crypto["symbol"], 
                   mentions=crypto["article_count"])
    
    # Add relationship edges
    for rel in crypto_relationships:
        # Only add if count is significant
        if rel["together_count"] > 1:
            G.add_edge(rel["crypto1"], rel["crypto2"], 
                      weight=rel["together_count"],
                      width=rel["together_count"] * 0.5)
    
    # Get node positions
    pos = nx.spring_layout(G, seed=42, k=0.4)
    
    # Get node sizes from attributes
    node_sizes = [G.nodes[node].get('size', 500) for node in G.nodes]
    
    # Get edge widths
    edge_widths = [G.edges[edge].get('width', 1) for edge in G.edges]
    
    # Draw the graph
    nodes = nx.draw_networkx_nodes(G, pos, node_size=node_sizes, 
                                   node_color="skyblue", alpha=0.8)
    edges = nx.draw_networkx_edges(G, pos, width=edge_widths, 
                                   edge_color="gray", alpha=0.5)
    
    # Add labels
    labels = {}
    for node in G.nodes:
        symbol = G.nodes[node].get('symbol', '')
        mentions = G.nodes[node].get('mentions', 0)
        labels[node] = f"{node} ({symbol})\n{mentions} mentions"
    
    nx.draw_networkx_labels(G, pos, labels, font_size=9, 
                           font_family="sans-serif", font_weight="bold")
    
    # Save figure
    plt.title("Cryptocurrency Relationship Network", size=16)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(STATIC_DIR, "crypto_network.png"), dpi=300, bbox_inches="tight")
    plt.close()
    
    print("Created cryptocurrency network visualization")

def create_topic_network(driver):
    """Create a visualization of topic relationships."""
    plt.figure(figsize=(12, 10))
    
    # Get topic nodes and their article counts
    with driver.session() as session:
        topic_counts = session.run("""
            MATCH (t:Topic)<-[:HAS_TOPIC]-(a:Article)
            RETURN t.name as name, count(a) as article_count
            ORDER BY article_count DESC
        """).data()
        
        topic_relationships = session.run("""
            MATCH (t1:Topic)<-[:HAS_TOPIC]-(a:Article)-[:HAS_TOPIC]->(t2:Topic)
            WHERE t1.name < t2.name
            RETURN t1.name as topic1, t2.name as topic2, 
                   count(a) as together_count
            ORDER BY together_count DESC
            LIMIT 25
        """).data()
    
    # Create graph
    G = nx.Graph()
    
    # Add topic nodes
    for topic in topic_counts:
        # Scale node size based on number of articles
        node_size = 500 + (topic["article_count"] * 50)
        G.add_node(topic["name"], size=node_size, 
                  articles=topic["article_count"])
    
    # Add relationship edges
    for rel in topic_relationships:
        if rel["together_count"] > 0:
            G.add_edge(rel["topic1"], rel["topic2"], 
                      weight=rel["together_count"],
                      width=rel["together_count"] * 0.8)
    
    # Get node positions
    pos = nx.spring_layout(G, seed=42, k=0.3)
    
    # Get node sizes from attributes
    node_sizes = [G.nodes[node].get('size', 500) for node in G.nodes]
    
    # Get edge widths
    edge_widths = [G.edges[edge].get('width', 1) for edge in G.edges]
    
    # Draw the graph
    nodes = nx.draw_networkx_nodes(G, pos, node_size=node_sizes, 
                                  node_color="lightgreen", alpha=0.8)
    edges = nx.draw_networkx_edges(G, pos, width=edge_widths, 
                                  edge_color="gray", alpha=0.5)
    
    # Add labels
    labels = {}
    for node in G.nodes:
        articles = G.nodes[node].get('articles', 0)
        labels[node] = f"{node}\n{articles} articles"
    
    nx.draw_networkx_labels(G, pos, labels, font_size=9, 
                           font_family="sans-serif", font_weight="bold")
    
    # Save figure
    plt.title("Topic Relationship Network", size=16)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(STATIC_DIR, "topic_network.png"), dpi=300, bbox_inches="tight")
    plt.close()
    
    print("Created topic network visualization")

def create_d3_data(driver):
    """Create D3.js compatible JSON data for interactive visualization."""
    with driver.session() as session:
        # Get all nodes
        crypto_result = session.run("""
            MATCH (c:Cryptocurrency)
            RETURN id(c) AS id, c.name AS name, 'Cryptocurrency' AS type, c.symbol AS symbol
        """)
        
        topic_result = session.run("""
            MATCH (t:Topic)
            RETURN id(t) AS id, t.name AS name, 'Topic' AS type
        """)
        
        article_result = session.run("""
            MATCH (a:Article)
            RETURN id(a) AS id, a.title AS name, 'Article' AS type
            LIMIT 15
        """)
        
        # Create nodes list
        nodes = []
        id_mapping = {}  # Map Neo4j IDs to array indices
        
        # Add cryptocurrency nodes
        idx = 0
        for record in crypto_result:
            id_mapping[record["id"]] = idx
            nodes.append({
                "id": idx,
                "name": record["name"],
                "type": record["type"],
                "symbol": record["symbol"],
                "group": 1
            })
            idx += 1
        
        # Add topic nodes
        for record in topic_result:
            id_mapping[record["id"]] = idx
            nodes.append({
                "id": idx,
                "name": record["name"],
                "type": record["type"],
                "group": 2
            })
            idx += 1
        
        # Add article nodes (limited)
        for record in article_result:
            id_mapping[record["id"]] = idx
            nodes.append({
                "id": idx,
                "name": record["name"],
                "type": record["type"],
                "group": 3
            })
            idx += 1
        
        # Get relationships
        rel_result = session.run("""
            MATCH (n1)-[r]-(n2)
            WHERE id(n1) IS NOT NULL AND id(n2) IS NOT NULL
            RETURN id(n1) AS source, id(n2) AS target, type(r) AS type
            LIMIT 150
        """)
        
        # Create links list
        links = []
        for record in rel_result:
            source_id = record["source"]
            target_id = record["target"]
            
            # Skip if source or target is not in our nodes list
            if source_id not in id_mapping or target_id not in id_mapping:
                continue
            
            links.append({
                "source": id_mapping[source_id],
                "target": id_mapping[target_id],
                "type": record["type"],
                "value": 1
            })
        
        # Create the final graph data
        graph_data = {
            "nodes": nodes,
            "links": links
        }
        
        # Save as JSON
        with open(os.path.join(STATIC_DIR, 'graph_data.json'), 'w') as f:
            json.dump(graph_data, f, indent=2)
        
        print("Created D3.js compatible graph data")

def create_graph_visualizations(driver):
    """Create all graph visualizations."""
    create_crypto_network(driver)
    create_topic_network(driver)
    create_d3_data(driver)

def process_markdown_files():
    """Process all markdown files in the directory."""
    print(f"Found {len(os.listdir(MARKDOWN_DIR))} markdown files")
    
    articles = []
    article_id = 1
    
    for filename in os.listdir(MARKDOWN_DIR):
        if filename.endswith('.md'):
            filepath = os.path.join(MARKDOWN_DIR, filename)
            
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Extract metadata and content using regex
            title_match = re.search(r'# (.+)', content)
            title = title_match.group(1) if title_match else "Untitled"
            
            date_match = re.search(r'Date: (\d{4}-\d{2}-\d{2})', content)
            date = date_match.group(1) if date_match else datetime.date.today().isoformat()
            
            source_match = re.search(r'Source: (.+)', content)
            source = source_match.group(1) if source_match else "Unknown"
            
            url_match = re.search(r'URL: (.+)', content)
            url = url_match.group(1) if url_match else ""
            
            # Extract summary and content
            summary = ""
            summary_match = re.search(r'Summary:(.*?)(?=\n\n|\n#|\n\*\*|$)', content, re.DOTALL)
            if summary_match:
                summary = summary_match.group(1).strip()
            
            # Extract main content (everything after metadata)
            main_content = content
            
            # Store article data
            article = {
                "id": f"article-{article_id}",
                "title": title,
                "date": date,
                "source": source,
                "url": url,
                "summary": summary,
                "content": main_content,
                "filename": filename
            }
            
            articles.append(article)
            article_id += 1
    
    print(f"Processed {len(articles)} articles")
    return articles

def import_to_neo4j(driver, articles):
    """Import articles and their relationships to Neo4j."""
    print(f"Importing {len(articles)} articles to Neo4j...")
    
    # Process in batches to avoid keeping a session open too long
    batch_size = 5
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(articles) + batch_size - 1)//batch_size}")
        
        with driver.session() as session:
            for article in batch:
                # Create Article node
                session.run("""
                    MERGE (a:Article {id: $id})
                    SET a.title = $title,
                        a.date = $date,
                        a.url = $url,
                        a.summary = $summary,
                        a.content = $content
                """, article)
                
                # Create Source node and relationship
                session.run("""
                    MERGE (s:Source {name: $source})
                    WITH s
                    MATCH (a:Article {id: $id})
                    MERGE (a)-[:FROM_SOURCE]->(s)
                """, {"id": article["id"], "source": article["source"]})
                
                # Extract cryptocurrencies mentioned
                session.run("""
                    MATCH (a:Article {id: $id})
                    
                    // Bitcoin (BTC)
                    WITH a, 
                         CASE WHEN toLower(a.content) CONTAINS 'bitcoin' OR toLower(a.content) CONTAINS 'btc' 
                              THEN true ELSE false END AS mentions_btc
                    WHERE mentions_btc
                    MERGE (c:Cryptocurrency {name: 'Bitcoin', symbol: 'BTC'})
                    MERGE (a)-[:MENTIONS_CRYPTO]->(c)
                    
                    // Ethereum (ETH)
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'ethereum' OR toLower(a.content) CONTAINS 'eth'
                    MERGE (c:Cryptocurrency {name: 'Ethereum', symbol: 'ETH'})
                    MERGE (a)-[:MENTIONS_CRYPTO]->(c)
                    
                    // Ripple (XRP)
                    WITH a 
                    WHERE toLower(a.content) CONTAINS 'ripple' OR toLower(a.content) CONTAINS 'xrp'
                    MERGE (c:Cryptocurrency {name: 'Ripple', symbol: 'XRP'})
                    MERGE (a)-[:MENTIONS_CRYPTO]->(c)
                    
                    // Solana (SOL)
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'solana' OR toLower(a.content) CONTAINS ' sol '
                    MERGE (c:Cryptocurrency {name: 'Solana', symbol: 'SOL'})
                    MERGE (a)-[:MENTIONS_CRYPTO]->(c)
                    
                    // Tether (USDT)
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'tether' OR toLower(a.content) CONTAINS 'usdt'
                    MERGE (c:Cryptocurrency {name: 'Tether', symbol: 'USDT'})
                    MERGE (a)-[:MENTIONS_CRYPTO]->(c)
                    
                    // Binance Coin (BNB)
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'binance coin' OR toLower(a.content) CONTAINS 'bnb'
                    MERGE (c:Cryptocurrency {name: 'Binance Coin', symbol: 'BNB'})
                    MERGE (a)-[:MENTIONS_CRYPTO]->(c)
                    
                    // Cardano (ADA)
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'cardano' OR toLower(a.content) CONTAINS 'ada'
                    MERGE (c:Cryptocurrency {name: 'Cardano', symbol: 'ADA'})
                    MERGE (a)-[:MENTIONS_CRYPTO]->(c)
                    
                    // Litecoin (LTC)
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'litecoin' OR toLower(a.content) CONTAINS 'ltc'
                    MERGE (c:Cryptocurrency {name: 'Litecoin', symbol: 'LTC'})
                    MERGE (a)-[:MENTIONS_CRYPTO]->(c)
                    
                    // Chainlink (LINK)
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'chainlink' OR toLower(a.content) CONTAINS 'link token'
                    MERGE (c:Cryptocurrency {name: 'Chainlink', symbol: 'LINK'})
                    MERGE (a)-[:MENTIONS_CRYPTO]->(c)
                    
                    // USD Coin (USDC)
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'usd coin' OR toLower(a.content) CONTAINS 'usdc'
                    MERGE (c:Cryptocurrency {name: 'USD Coin', symbol: 'USDC'})
                    MERGE (a)-[:MENTIONS_CRYPTO]->(c)
                """, {"id": article["id"]})
                
                # Create Topics
                session.run("""
                    MATCH (a:Article {id: $id})
                    
                    // Topic: Blockchain Technology
                    WITH a, 
                         CASE WHEN toLower(a.content) CONTAINS 'blockchain' OR toLower(a.content) CONTAINS 'distributed ledger'
                              THEN true ELSE false END AS blockchain_topic
                    WHERE blockchain_topic
                    MERGE (t:Topic {name: 'Blockchain Technology'})
                    MERGE (a)-[:HAS_TOPIC]->(t)
                    
                    // Topic: DeFi
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'defi' OR toLower(a.content) CONTAINS 'decentralized finance'
                    MERGE (t:Topic {name: 'DeFi'})
                    MERGE (a)-[:HAS_TOPIC]->(t)
                    
                    // Topic: NFT
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'nft' OR toLower(a.content) CONTAINS 'non-fungible token'
                    MERGE (t:Topic {name: 'NFT'})
                    MERGE (a)-[:HAS_TOPIC]->(t)
                    
                    // Topic: Regulation
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'regulation' OR toLower(a.content) CONTAINS 'sec' OR 
                          toLower(a.content) CONTAINS 'compliance' OR toLower(a.content) CONTAINS 'regulatory'
                    MERGE (t:Topic {name: 'Regulation'})
                    MERGE (a)-[:HAS_TOPIC]->(t)
                    
                    // Topic: Trading
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'trading' OR toLower(a.content) CONTAINS 'exchange'
                    MERGE (t:Topic {name: 'Trading'})
                    MERGE (a)-[:HAS_TOPIC]->(t)
                    
                    // Topic: Mining
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'mining' OR toLower(a.content) CONTAINS 'miner'
                    MERGE (t:Topic {name: 'Mining'})
                    MERGE (a)-[:HAS_TOPIC]->(t)
                    
                    // Topic: Price Movement
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'price' OR toLower(a.content) CONTAINS 'market'
                    MERGE (t:Topic {name: 'Price Movement'})
                    MERGE (a)-[:HAS_TOPIC]->(t)
                    
                    // Topic: Stablecoins
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'stablecoin' OR toLower(a.content) CONTAINS 'usdt' OR 
                          toLower(a.content) CONTAINS 'usdc'
                    MERGE (t:Topic {name: 'Stablecoins'})
                    MERGE (a)-[:HAS_TOPIC]->(t)
                    
                    // Topic: Institutional Adoption
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'institutional' OR toLower(a.content) CONTAINS 'company buys' OR
                          toLower(a.content) CONTAINS 'adoption'
                    MERGE (t:Topic {name: 'Institutional Adoption'})
                    MERGE (a)-[:HAS_TOPIC]->(t)
                    
                    // Topic: Politics
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'politics' OR toLower(a.content) CONTAINS 'government' OR
                          toLower(a.content) CONTAINS 'biden' OR toLower(a.content) CONTAINS 'congress'
                    MERGE (t:Topic {name: 'Politics'})
                    MERGE (a)-[:HAS_TOPIC]->(t)
                    
                    // Topic: ETF
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'etf' OR toLower(a.content) CONTAINS 'exchange-traded fund'
                    MERGE (t:Topic {name: 'ETF'})
                    MERGE (a)-[:HAS_TOPIC]->(t)
                    
                    // Topic: Layer 2
                    WITH a
                    WHERE toLower(a.content) CONTAINS 'layer 2' OR toLower(a.content) CONTAINS 'l2' OR
                          toLower(a.content) CONTAINS 'scaling'
                    MERGE (t:Topic {name: 'Layer 2'})
                    MERGE (a)-[:HAS_TOPIC]->(t)
                """, {"id": article["id"]})
                
                # Extract persons mentioned
                session.run("""
                    MATCH (a:Article {id: $id})
                    WITH a, $content AS text
                    UNWIND split(text, ' ') AS word
                    WITH a, word
                    WHERE size(word) > 1 
                          AND left(word, 1) = '@'
                          AND word <> '@'
                    WITH a, replace(word, '@', '') AS person_name
                    MERGE (p:Person {name: person_name})
                    MERGE (a)-[:MENTIONS_PERSON]->(p)
                """, {"id": article["id"], "content": article["content"]})
    
    print("Data import complete!")

def run_analytics(driver):
    """Run analytics queries to understand the data."""
    with driver.session() as session:
        # Get node counts
        node_counts = session.run("""
            MATCH (n)
            RETURN labels(n)[0] AS label, count(n) AS count
            ORDER BY count DESC
        """).data()
        
        print("\nNode counts:")
        for item in node_counts:
            print(f"  {item['label']}: {item['count']}")
        
        # Top cryptocurrencies
        top_cryptos = session.run("""
            MATCH (c:Cryptocurrency)<-[r:MENTIONS_CRYPTO]-(a:Article)
            RETURN c.name AS name, c.symbol AS symbol, count(r) AS mentions
            ORDER BY mentions DESC
        """).data()
        
        print("\nTop mentioned cryptocurrencies:")
        for crypto in top_cryptos:
            print(f"  {crypto['name']} ({crypto['symbol']}): {crypto['mentions']} mentions")
        
        # Top topics
        top_topics = session.run("""
            MATCH (t:Topic)<-[r:HAS_TOPIC]-(a:Article)
            RETURN t.name AS name, count(r) AS article_count
            ORDER BY article_count DESC
        """).data()
        
        print("\nTop topics:")
        for topic in top_topics:
            print(f"  {topic['name']}: {topic['article_count']} articles")
        
        # Top relationships between cryptocurrencies
        crypto_relationships = session.run("""
            MATCH (c1:Cryptocurrency)<-[:MENTIONS_CRYPTO]-(a:Article)-[:MENTIONS_CRYPTO]->(c2:Cryptocurrency)
            WHERE c1 <> c2
            RETURN c1.name AS crypto1, c2.name AS crypto2, count(a) AS together_count
            ORDER BY together_count DESC
            LIMIT 8
        """).data()
        
        print("\nStrongest cryptocurrency relationships:")
        for rel in crypto_relationships:
            print(f"  {rel['crypto1']} - {rel['crypto2']}: mentioned together in {rel['together_count']} articles")

def build_graph():
    """Build the entire graph from markdown files."""
    print("\nStarting GraphRAG build process...")
    
    # Connect to Neo4j
    driver = connect_to_neo4j()
    
    # Set up schema
    setup_schema(driver)
    
    # Process markdown files
    articles = process_markdown_files()
    
    # Import to Neo4j
    import_to_neo4j(driver, articles)
    
    # Run analytics
    run_analytics(driver)
    
    # Create graph visualizations
    create_graph_visualizations(driver)
    
    # Close connection
    driver.close()
    
    print("\nCrypto news graph build complete!")
    return True

def main():
    """Main function to run the build graph process."""
    # Build the graph
    build_graph()

if __name__ == "__main__":
    main() 