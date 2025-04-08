"""
Neo4j Connector Module

This module handles connections to Neo4j and basic operations.
"""

import os
import sys
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Neo4j connection parameters
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class Neo4jConnector:
    """Class to handle Neo4j connection and operations."""
    
    def __init__(self, uri: str = None, username: str = None, password: str = None):
        """
        Initialize the Neo4j connector.
        
        Args:
            uri: Neo4j URI (defaults to environment variable)
            username: Neo4j username (defaults to environment variable)
            password: Neo4j password (defaults to environment variable)
        """
        self.uri = uri or NEO4J_URI
        self.username = username or NEO4J_USER
        self.password = password or NEO4J_PASSWORD
        self.driver = None
    
    def connect(self) -> bool:
        """
        Connect to Neo4j database.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                connection_test = result.single()["test"]
                print(f"Neo4j connection test: {connection_test}")
                print("Successfully connected to Neo4j!")
            
            return True
        except Exception as e:
            print(f"Error connecting to Neo4j: {e}")
            return False
    
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            print("Neo4j connection closed.")
    
    def run_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict]:
        """
        Run a Cypher query and return the results.
        
        Args:
            query: Cypher query
            params: Query parameters
            
        Returns:
            List of results as dictionaries
        """
        if not self.driver:
            if not self.connect():
                return []
        
        try:
            with self.driver.session() as session:
                result = session.run(query, params or {})
                return [dict(record) for record in result]
        except Exception as e:
            print(f"Error running query: {e}")
            return []
    
    def clear_database(self) -> bool:
        """
        Clear all data from the database.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            if not self.connect():
                return False
        
        try:
            with self.driver.session() as session:
                # Delete all relationships and nodes
                session.run("MATCH (n) DETACH DELETE n")
                print("Database cleared successfully.")
                return True
        except Exception as e:
            print(f"Error clearing database: {e}")
            return False
    
    def get_node_counts(self) -> Dict[str, int]:
        """
        Get counts of nodes by label.
        
        Returns:
            Dictionary mapping labels to counts
        """
        if not self.driver:
            if not self.connect():
                return {}
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n)
                    RETURN labels(n)[0] AS label, count(n) AS count
                    ORDER BY count DESC
                """)
                
                return {record["label"]: record["count"] for record in result}
        except Exception as e:
            print(f"Error getting node counts: {e}")
            return {}
    
    def get_relationship_counts(self) -> Dict[str, int]:
        """
        Get counts of relationships by type.
        
        Returns:
            Dictionary mapping relationship types to counts
        """
        if not self.driver:
            if not self.connect():
                return {}
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) AS type, count(r) AS count
                    ORDER BY count DESC
                """)
                
                return {record["type"]: record["count"] for record in result}
        except Exception as e:
            print(f"Error getting relationship counts: {e}")
            return {}
    
    def import_article(self, article: Dict[str, Any]) -> bool:
        """
        Import an article into Neo4j.
        
        Args:
            article: Article data
            
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            if not self.connect():
                return False
        
        try:
            with self.driver.session() as session:
                # Create Article node
                session.run("""
                    MERGE (a:Article {id: $id})
                    SET a.title = $title,
                        a.date = $date,
                        a.url = $url,
                        a.summary = $summary,
                        a.content = $content
                """, {
                    "id": article.get("id", f"article-{article.get('url', '')}"),
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
                        "id": article.get("id", f"article-{article.get('url', '')}"),
                        "source": article.get("source", "")
                    })
                
                return True
        except Exception as e:
            print(f"Error importing article: {e}")
            return False

def get_connector() -> Neo4jConnector:
    """
    Get a Neo4j connector instance.
    
    Returns:
        Neo4jConnector instance
    """
    connector = Neo4jConnector()
    connector.connect()
    return connector 