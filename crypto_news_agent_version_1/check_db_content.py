import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

# Neo4j connection parameters
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def connect_to_neo4j():
    """Connect to Neo4j database and return driver."""
    try:
        driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        print("Successfully connected to Neo4j!")
        return driver
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        return None

def check_node_counts(driver):
    """Check the counts of different node types."""
    with driver.session() as session:
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] AS label, count(n) AS count
            ORDER BY count DESC
        """)
        
        print("\n=== Node Counts ===")
        for record in result:
            print(f"{record['label']}: {record['count']}")

def check_relationship_counts(driver):
    """Check the counts of different relationship types."""
    with driver.session() as session:
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) AS type, count(r) AS count
            ORDER BY count DESC
        """)
        
        print("\n=== Relationship Counts ===")
        for record in result:
            print(f"{record['type']}: {record['count']}")

def check_cryptocurrency_nodes(driver):
    """Check all cryptocurrency nodes."""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Cryptocurrency)
            RETURN c.name AS name, c.symbol AS symbol
            ORDER BY c.name
        """)
        
        print("\n=== Cryptocurrency Nodes ===")
        for record in result:
            print(f"{record['name']} ({record['symbol'] if record.get('symbol') else 'No symbol'})")

def check_cryptocurrency_mentions(driver):
    """Check all cryptocurrency mentions in articles."""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Cryptocurrency)<-[r:MENTIONS_CRYPTO]-(a:Article)
            RETURN c.name AS cryptocurrency, count(a) AS mention_count
            ORDER BY mention_count DESC
            LIMIT 10
        """)
        
        print("\n=== Top Cryptocurrency Mentions ===")
        for record in result:
            print(f"{record['cryptocurrency']}: {record['mention_count']} mentions")

def main():
    """Main function to check database content."""
    print("Checking Neo4j Database Content")
    print("===============================")
    
    driver = connect_to_neo4j()
    if not driver:
        print("Could not connect to Neo4j database.")
        return
    
    try:
        check_node_counts(driver)
        check_relationship_counts(driver)
        check_cryptocurrency_nodes(driver)
        check_cryptocurrency_mentions(driver)
    except Exception as e:
        print(f"Error checking database content: {e}")
    
    driver.close()
    print("\nDatabase check complete.")

if __name__ == "__main__":
    main() 