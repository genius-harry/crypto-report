"""
Neo4j Schema Module

This module handles Neo4j schema creation and management.
"""

from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase

from .neo4j_connector import Neo4jConnector

def setup_schema(connector: Neo4jConnector) -> bool:
    """
    Set up the Neo4j schema with constraints and indexes.
    
    Args:
        connector: Neo4j connector
        
    Returns:
        True if successful, False otherwise
    """
    if not connector.driver:
        if not connector.connect():
            return False
    
    try:
        # Create constraints for unique nodes
        constraints = [
            "CREATE CONSTRAINT article_id IF NOT EXISTS FOR (a:Article) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT cryptocurrency_name IF NOT EXISTS FOR (c:Cryptocurrency) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT source_name IF NOT EXISTS FOR (s:Source) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
        ]
        
        # Run each constraint query
        with connector.driver.session() as session:
            for constraint_query in constraints:
                session.run(constraint_query)
        
        print("Neo4j schema setup complete!")
        return True
    except Exception as e:
        print(f"Error setting up schema: {e}")
        return False

def clean_schema(connector: Neo4jConnector) -> bool:
    """
    Clean up the Neo4j schema by dropping all constraints and indexes.
    
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
            # Get all constraints
            constraints_result = session.run("SHOW CONSTRAINTS")
            constraints = [record.get("name") for record in constraints_result if record.get("name")]
            
            # Drop each constraint
            for constraint in constraints:
                try:
                    session.run(f"DROP CONSTRAINT {constraint}")
                    print(f"Dropped constraint: {constraint}")
                except Exception as e:
                    print(f"Error dropping constraint {constraint}: {e}")
            
            # Get all indexes
            indexes_result = session.run("SHOW INDEXES")
            indexes = [record.get("name") for record in indexes_result if record.get("name") and record.get("name") not in constraints]
            
            # Drop each index
            for index in indexes:
                try:
                    session.run(f"DROP INDEX {index}")
                    print(f"Dropped index: {index}")
                except Exception as e:
                    print(f"Error dropping index {index}: {e}")
            
            print("Schema cleanup complete!")
            return True
    except Exception as e:
        print(f"Error cleaning schema: {e}")
        return False

def create_indexes(connector: Neo4jConnector) -> bool:
    """
    Create additional indexes for better query performance.
    
    Args:
        connector: Neo4j connector
        
    Returns:
        True if successful, False otherwise
    """
    if not connector.driver:
        if not connector.connect():
            return False
    
    try:
        # Define indexes to create
        indexes = [
            "CREATE INDEX article_date IF NOT EXISTS FOR (a:Article) ON (a.date)",
            "CREATE INDEX article_title IF NOT EXISTS FOR (a:Article) ON (a.title)",
            "CREATE INDEX cryptocurrency_symbol IF NOT EXISTS FOR (c:Cryptocurrency) ON (c.symbol)",
        ]
        
        # Run each index query
        with connector.driver.session() as session:
            for index_query in indexes:
                session.run(index_query)
        
        print("Created additional indexes!")
        return True
    except Exception as e:
        print(f"Error creating indexes: {e}")
        return False 