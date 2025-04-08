"""
Neo4j Database Cleanup Utility

This script helps clean up the Neo4j database.
"""

import os
import sys
from dotenv import load_dotenv
from .neo4j_connector import Neo4jConnector
from .schema import clean_schema

# Load environment variables
load_dotenv()

def clean_database(force: bool = False) -> bool:
    """
    Clean the Neo4j database.
    
    Args:
        force: Whether to force cleanup without confirmation
        
    Returns:
        True if successful, False otherwise
    """
    # Connect to Neo4j
    connector = Neo4jConnector()
    if not connector.connect():
        print("Failed to connect to Neo4j database.")
        return False
    
    # Get database info
    nodes = connector.get_node_counts()
    relationships = connector.get_relationship_counts()
    
    # Print database info
    print("\nCurrent Neo4j Database Status:")
    print("-" * 30)
    print("Nodes:")
    for label, count in nodes.items():
        print(f"  {label}: {count}")
    
    print("\nRelationships:")
    for rel, count in relationships.items():
        print(f"  {rel}: {count}")
    
    total_nodes = sum(nodes.values())
    total_rels = sum(relationships.values())
    print(f"\nTotal: {total_nodes} nodes, {total_rels} relationships")
    
    if total_nodes == 0 and total_rels == 0:
        print("\nDatabase is already empty.")
        connector.close()
        return True
    
    # Ask for confirmation
    if not force:
        confirmation = input("\nDo you want to delete all data? (y/n): ")
        if confirmation.lower() != 'y':
            print("Cleanup aborted.")
            connector.close()
            return False
    
    # Clean schema and data
    print("\nCleaning database...")
    clean_schema(connector)
    connector.clear_database()
    
    # Verify cleanup
    nodes = connector.get_node_counts()
    relationships = connector.get_relationship_counts()
    total_nodes = sum(nodes.values())
    total_rels = sum(relationships.values())
    
    if total_nodes == 0 and total_rels == 0:
        print("Database cleaned successfully!")
        connector.close()
        return True
    else:
        print(f"Warning: Database still has {total_nodes} nodes and {total_rels} relationships.")
        connector.close()
        return False

if __name__ == "__main__":
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="Neo4j Database Cleanup Utility")
    parser.add_argument("--force", action="store_true", help="Force cleanup without confirmation")
    args = parser.parse_args()
    
    # Clean database
    if clean_database(args.force):
        sys.exit(0)
    else:
        sys.exit(1) 