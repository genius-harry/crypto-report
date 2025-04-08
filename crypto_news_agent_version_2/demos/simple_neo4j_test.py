"""
Simple Neo4j Test
"""

from neo4j import GraphDatabase

# Neo4j connection parameters
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "Yaoyiran20061111"

def run_test():
    """Run a simple Neo4j test."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # Basic connectivity test
        result = session.run("RETURN 1 as one")
        print(f"Connection test: {result.single()['one']}")
        
        try:
            # Try to list available procedures
            result = session.run("SHOW PROCEDURES")
            print("\nAvailable procedures:")
            for record in result:
                print(f"  - {record['name']}")
                
            # Check if any APOC procedures are available
            result = session.run("SHOW PROCEDURES YIELD name WHERE name CONTAINS 'apoc' RETURN count(*) as apocCount")
            apoc_count = result.single()["apocCount"]
            print(f"\nAPOC procedures available: {apoc_count}")
            
            if apoc_count > 0:
                print("✅ APOC is installed!")
            else:
                print("❌ APOC is NOT installed or enabled. Install it in Neo4j Desktop.")
                
        except Exception as e:
            print(f"Error querying procedures: {e}")
    
    driver.close()

if __name__ == "__main__":
    run_test() 