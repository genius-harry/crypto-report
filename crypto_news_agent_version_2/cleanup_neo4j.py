#!/usr/bin/env python

"""
Neo4j Database Cleanup Script

A command-line utility to clean up the Neo4j database.
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Import the cleanup function
from modules.graph_builder.cleanup_neo4j import clean_database

if __name__ == "__main__":
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="Neo4j Database Cleanup Utility")
    parser.add_argument("--force", action="store_true", help="Force cleanup without confirmation")
    args = parser.parse_args()
    
    # Print header
    print("\nNeo4j Database Cleanup Utility")
    print("=============================\n")
    
    # Clean database
    if clean_database(args.force):
        print("\nCleanup successful!")
        sys.exit(0)
    else:
        print("\nCleanup failed or was aborted.")
        sys.exit(1) 