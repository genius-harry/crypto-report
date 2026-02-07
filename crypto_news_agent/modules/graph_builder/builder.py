"""
Graph Builder Module

This module handles building the Neo4j graph from article data.
"""

import os
import re
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase

from .neo4j_connector import Neo4jConnector
from .schema import setup_schema, clean_schema, create_indexes

def process_batch(connector: Neo4jConnector, batch: List[Dict[str, Any]]) -> bool:
    """
    Process a batch of articles and import them into Neo4j.
    
    Args:
        connector: Neo4j connector
        batch: List of article data
        
    Returns:
        True if successful, False otherwise
    """
    if not connector.driver:
        if not connector.connect():
            return False
    
    try:
        with connector.driver.session() as session:
            for article in batch:
                article_id = article.get("id", f"article-{article.get('url', '')}")
                
                # Create Article node
                session.run("""
                    MERGE (a:Article {id: $id})
                    SET a.title = $title,
                        a.date = $date,
                        a.url = $url,
                        a.summary = $summary,
                        a.content = $content
                """, {
                    "id": article_id,
                    "title": article.get("title", ""),
                    "date": article.get("date", ""),
                    "url": article.get("url", ""),
                    "summary": article.get("description", ""),
                    "content": article.get("content", "")
                })
                
                # Create Source node and relationship
                if article.get("source"):
                    session.run("""
                        MERGE (s:Source {name: $source})
                        WITH s
                        MATCH (a:Article {id: $id})
                        MERGE (a)-[:FROM_SOURCE]->(s)
                    """, {
                        "id": article_id,
                        "source": article.get("source", "")
                    })
                
                # Process cryptocurrency mentions
                extract_cryptocurrencies(session, article_id, article.get("content", ""))
                
                # Process topics
                extract_topics(session, article_id, article.get("content", ""))
                
                # Process person mentions
                extract_persons(session, article_id, article.get("content", ""))
        
        return True
    except Exception as e:
        print(f"Error processing batch: {e}")
        return False

def extract_cryptocurrencies(session, article_id: str, content: str):
    """
    Extract cryptocurrency mentions from article content.
    
    Args:
        session: Neo4j session
        article_id: Article ID
        content: Article content
    """
    try:
        # Define cryptocurrency patterns
        crypto_patterns = [
            # Bitcoin (BTC)
            {"name": "Bitcoin", "symbol": "BTC", "patterns": ["bitcoin", "btc"]},
            # Ethereum (ETH)
            {"name": "Ethereum", "symbol": "ETH", "patterns": ["ethereum", "eth"]},
            # Ripple (XRP)
            {"name": "Ripple", "symbol": "XRP", "patterns": ["ripple", "xrp"]},
            # Solana (SOL)
            {"name": "Solana", "symbol": "SOL", "patterns": ["solana", " sol "]},
            # Tether (USDT)
            {"name": "Tether", "symbol": "USDT", "patterns": ["tether", "usdt"]},
            # Binance Coin (BNB)
            {"name": "Binance Coin", "symbol": "BNB", "patterns": ["binance coin", "bnb"]},
            # Cardano (ADA)
            {"name": "Cardano", "symbol": "ADA", "patterns": ["cardano", "ada"]},
            # Litecoin (LTC)
            {"name": "Litecoin", "symbol": "LTC", "patterns": ["litecoin", "ltc"]},
            # Chainlink (LINK)
            {"name": "Chainlink", "symbol": "LINK", "patterns": ["chainlink", "link token"]},
            # USD Coin (USDC)
            {"name": "USD Coin", "symbol": "USDC", "patterns": ["usd coin", "usdc"]},
        ]
        
        content_lower = content.lower()
        
        for crypto in crypto_patterns:
            for pattern in crypto["patterns"]:
                if pattern in content_lower:
                    session.run("""
                        MATCH (a:Article {id: $article_id})
                        MERGE (c:Cryptocurrency {name: $name})
                        SET c.symbol = $symbol
                        MERGE (a)-[:MENTIONS_CRYPTO]->(c)
                    """, {
                        "article_id": article_id,
                        "name": crypto["name"],
                        "symbol": crypto["symbol"]
                    })
                    break  # Only need to match once per cryptocurrency
    except Exception as e:
        print(f"Error extracting cryptocurrencies: {e}")

def extract_topics(session, article_id: str, content: str):
    """
    Extract topics from article content.
    
    Args:
        session: Neo4j session
        article_id: Article ID
        content: Article content
    """
    try:
        # Define topic patterns
        topic_patterns = [
            {"name": "Blockchain Technology", "patterns": ["blockchain", "distributed ledger"]},
            {"name": "DeFi", "patterns": ["defi", "decentralized finance"]},
            {"name": "NFT", "patterns": ["nft", "non-fungible token"]},
            {"name": "Regulation", "patterns": ["regulation", "sec", "compliance", "regulatory"]},
            {"name": "Trading", "patterns": ["trading", "exchange"]},
            {"name": "Mining", "patterns": ["mining", "miner"]},
            {"name": "Price Movement", "patterns": ["price", "market"]},
            {"name": "Stablecoins", "patterns": ["stablecoin", "usdt", "usdc"]},
            {"name": "Institutional Adoption", "patterns": ["institutional", "company buys", "adoption"]},
            {"name": "Politics", "patterns": ["politics", "government", "biden", "congress"]},
            {"name": "ETF", "patterns": ["etf", "exchange-traded fund"]},
            {"name": "Layer 2", "patterns": ["layer 2", "l2", "scaling"]}
        ]
        
        content_lower = content.lower()
        
        for topic in topic_patterns:
            for pattern in topic["patterns"]:
                if pattern in content_lower:
                    session.run("""
                        MATCH (a:Article {id: $article_id})
                        MERGE (t:Topic {name: $name})
                        MERGE (a)-[:HAS_TOPIC]->(t)
                    """, {
                        "article_id": article_id,
                        "name": topic["name"]
                    })
                    break  # Only need to match once per topic
    except Exception as e:
        print(f"Error extracting topics: {e}")

def extract_persons(session, article_id: str, content: str):
    """
    Extract person mentions from article content.
    
    Args:
        session: Neo4j session
        article_id: Article ID
        content: Article content
    """
    try:
        # Extract words starting with @ as potential Twitter handles
        words = content.split()
        person_handles = []
        
        for word in words:
            if word.startswith("@") and len(word) > 1:
                person_handles.append(word[1:])  # Remove @
        
        # Add each person
        for handle in person_handles:
            session.run("""
                MATCH (a:Article {id: $article_id})
                MERGE (p:Person {name: $name})
                MERGE (a)-[:MENTIONS_PERSON]->(p)
            """, {
                "article_id": article_id,
                "name": handle
            })
    except Exception as e:
        print(f"Error extracting persons: {e}")

def create_relationships(connector: Neo4jConnector) -> bool:
    """
    Create relationships between entities in the graph.
    
    Args:
        connector: Neo4j connector
        
    Returns:
        True if successful, False otherwise
    """
    if not connector.driver:
        if not connector.connect():
            return False
    
    try:
        with connector.driver.session() as session:
            # Create relationships between cryptocurrencies that appear in the same articles
            session.run("""
                MATCH (c1:Cryptocurrency)<-[:MENTIONS_CRYPTO]-(a:Article)-[:MENTIONS_CRYPTO]->(c2:Cryptocurrency)
                WHERE c1 <> c2
                WITH c1, c2, count(a) AS common_articles
                MERGE (c1)-[r:RELATED_TO]-(c2)
                SET r.common_articles = common_articles
            """)
            
            # Create relationships between topics that appear in the same articles
            session.run("""
                MATCH (t1:Topic)<-[:HAS_TOPIC]-(a:Article)-[:HAS_TOPIC]->(t2:Topic)
                WHERE t1 <> t2
                WITH t1, t2, count(a) AS common_articles
                MERGE (t1)-[r:RELATED_TOPIC]->(t2)
                SET r.common_articles = common_articles
            """)
            
            # Create relationships between persons and cryptocurrencies
            session.run("""
                MATCH (p:Person)<-[:MENTIONS_PERSON]-(a:Article)-[:MENTIONS_CRYPTO]->(c:Cryptocurrency)
                WITH p, c, count(a) AS mentions
                MERGE (p)-[r:DISCUSSES]->(c)
                SET r.mentions = mentions
            """)
            
            print("Created relationships between entities!")
            return True
    except Exception as e:
        print(f"Error creating relationships: {e}")
        return False

def run_analytics(connector: Neo4jConnector) -> Dict[str, Any]:
    """
    Run analytics queries on the graph.
    
    Args:
        connector: Neo4j connector
        
    Returns:
        Dictionary of analytics results
    """
    analytics = {}
    
    if not connector.driver:
        if not connector.connect():
            return analytics
    
    try:
        # Get node counts
        analytics["node_counts"] = connector.get_node_counts()
        
        # Get relationship counts
        analytics["relationship_counts"] = connector.get_relationship_counts()
        
        # Get top cryptocurrencies by mentions
        with connector.driver.session() as session:
            result = session.run("""
                MATCH (c:Cryptocurrency)<-[r:MENTIONS_CRYPTO]-(a:Article)
                RETURN c.name AS name, c.symbol AS symbol, count(r) AS mentions
                ORDER BY mentions DESC
            """)
            
            analytics["top_cryptocurrencies"] = [
                {"name": record["name"], "symbol": record["symbol"], "mentions": record["mentions"]}
                for record in result
            ]
            
            # Get top topics
            result = session.run("""
                MATCH (t:Topic)<-[r:HAS_TOPIC]-(a:Article)
                RETURN t.name AS name, count(r) AS article_count
                ORDER BY article_count DESC
            """)
            
            analytics["top_topics"] = [
                {"name": record["name"], "article_count": record["article_count"]}
                for record in result
            ]
            
            # Get top sources
            result = session.run("""
                MATCH (s:Source)<-[r:FROM_SOURCE]-(a:Article)
                RETURN s.name AS name, count(r) AS article_count
                ORDER BY article_count DESC
                LIMIT 10
            """)
            
            analytics["top_sources"] = [
                {"name": record["name"], "article_count": record["article_count"]}
                for record in result
            ]
            
            # Get strongest cryptocurrency relationships
            result = session.run("""
                MATCH (c1:Cryptocurrency)-[r:RELATED_TO]-(c2:Cryptocurrency)
                WHERE c1.name < c2.name  // Avoid duplicates
                RETURN c1.name AS crypto1, c2.name AS crypto2, r.common_articles AS together_count
                ORDER BY together_count DESC
                LIMIT 10
            """)
            
            analytics["strongest_crypto_relationships"] = [
                {"crypto1": record["crypto1"], "crypto2": record["crypto2"], "together_count": record["together_count"]}
                for record in result
            ]
        
        # Print analytics results
        print("\nNode counts:")
        for label, count in analytics["node_counts"].items():
            print(f"  {label}: {count}")
        
        print("\nTop mentioned cryptocurrencies:")
        for crypto in analytics["top_cryptocurrencies"]:
            print(f"  {crypto['name']} ({crypto['symbol']}): {crypto['mentions']} mentions")
        
        print("\nTop topics:")
        for topic in analytics["top_topics"]:
            print(f"  {topic['name']}: {topic['article_count']} articles")
        
        print("\nStrongest cryptocurrency relationships:")
        for rel in analytics["strongest_crypto_relationships"]:
            print(f"  {rel['crypto1']} - {rel['crypto2']}: mentioned together in {rel['together_count']} articles")
        
        return analytics
    
    except Exception as e:
        print(f"Error running analytics: {e}")
        return analytics

def build_graph(articles: List[Dict[str, Any]], clear_existing: bool = True) -> Dict[str, Any]:
    """
    Build the graph from a list of articles.
    
    Args:
        articles: List of article data
        clear_existing: Whether to clear existing data
        
    Returns:
        Dictionary of analytics results
    """
    print(f"Building graph from {len(articles)} articles...")
    
    # Connect to Neo4j
    connector = Neo4jConnector()
    if not connector.connect():
        return {}
    
    # Clean up database if requested
    if clear_existing:
        clean_schema(connector)
        connector.clear_database()
    
    # Set up schema
    setup_schema(connector)
    create_indexes(connector)
    
    # Process articles in batches
    batch_size = 5
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(articles) + batch_size - 1)//batch_size}")
        process_batch(connector, batch)
    
    # Create relationships
    create_relationships(connector)
    
    # Run analytics
    analytics = run_analytics(connector)
    
    # Close connection
    connector.close()
    
    print("Graph build complete!")
    return analytics 