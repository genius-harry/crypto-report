"""
Test Neo4j Connection

This script tests the basic connection to Neo4j and creates a sample crypto graph.
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

# Neo4j connection parameters
NEO4J_URI = "bolt://localhost:7687"  # Default Neo4j URI
NEO4J_USERNAME = "neo4j"             # Default username
NEO4J_PASSWORD = "Yaoyiran20061111"  # Your password

def test_connection():
    """Test connection to Neo4j database."""
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

def create_sample_graph(driver):
    """Create a sample graph with crypto-related data."""
    with driver.session() as session:
        # Clear existing data
        session.run("MATCH (n) DETACH DELETE n")
        
        # Create some crypto entities and relationships
        session.run("""
            CREATE (btc:Cryptocurrency {name: 'Bitcoin', symbol: 'BTC', price: 66000})
            CREATE (eth:Cryptocurrency {name: 'Ethereum', symbol: 'ETH', price: 3500})
            CREATE (sol:Cryptocurrency {name: 'Solana', symbol: 'SOL', price: 145})
            
            CREATE (satoshi:Person {name: 'Satoshi Nakamoto'})
            CREATE (vitalik:Person {name: 'Vitalik Buterin'})
            
            CREATE (btcWhitepaper:Document {title: 'Bitcoin: A Peer-to-Peer Electronic Cash System', year: 2008})
            CREATE (ethWhitepaper:Document {title: 'Ethereum: A Next-Generation Smart Contract and Decentralized Application Platform', year: 2013})
            
            CREATE (pow:Concept {name: 'Proof of Work'})
            CREATE (pos:Concept {name: 'Proof of Stake'})
            
            CREATE (satoshi)-[:CREATED]->(btc)
            CREATE (satoshi)-[:AUTHORED]->(btcWhitepaper)
            CREATE (btcWhitepaper)-[:DESCRIBES]->(btc)
            CREATE (btc)-[:USES]->(pow)
            
            CREATE (vitalik)-[:CREATED]->(eth)
            CREATE (vitalik)-[:AUTHORED]->(ethWhitepaper)
            CREATE (ethWhitepaper)-[:DESCRIBES]->(eth)
            CREATE (eth)-[:USES]->(pos)
            CREATE (eth)-[:RELATED_TO {relationship_type: 'competitor'}]->(sol)
        """)
        print("Sample crypto graph created!")
        
def run_test_query(driver):
    """Run a test Cypher query to verify the graph."""
    with driver.session() as session:
        print("\nRunning test queries:")
        
        # Test query 1: Count all nodes
        result = session.run("MATCH (n) RETURN count(n) as nodeCount")
        print(f"Total nodes: {result.single()['nodeCount']}")
        
        # Test query 2: Get all cryptocurrencies
        result = session.run("MATCH (c:Cryptocurrency) RETURN c.name as name, c.symbol as symbol, c.price as price")
        print("\nCryptocurrencies:")
        for record in result:
            print(f"  {record['name']} ({record['symbol']}): ${record['price']}")
            
        # Test query 3: Find Bitcoin creator
        result = session.run("""
            MATCH (p:Person)-[:CREATED]->(c:Cryptocurrency {name: 'Bitcoin'})
            RETURN p.name as creator
        """)
        creator = result.single()['creator']
        print(f"\nBitcoin creator: {creator}")

def main():
    """Main function to test Neo4j connection and create a sample graph."""
    print("Neo4j Connection Test")
    print("====================\n")
    
    # Test connection
    driver = test_connection()
    if not driver:
        print("Connection test failed. Please check your Neo4j instance and credentials.")
        return
    
    # Create sample data
    create_sample_graph(driver)
    
    # Run test query
    run_test_query(driver)
    
    # Close connection
    driver.close()
    print("\nNeo4j connection closed.")
    print("Test completed successfully!")

if __name__ == "__main__":
    main() 