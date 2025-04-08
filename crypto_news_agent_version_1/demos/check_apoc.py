"""
Check if APOC is installed in Neo4j
"""

from neo4j import GraphDatabase

# Neo4j connection parameters
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "Yaoyiran20061111"

def check_apoc():
    """Check if APOC is installed and available."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # Check for APOC procedures
        result = session.run("""
            CALL dbms.procedures()
            YIELD name
            WHERE name CONTAINS 'apoc'
            RETURN count(name) as apocProcedures
        """)
        apoc_count = result.single()["apocProcedures"]
        
        print(f"APOC procedures available: {apoc_count}")
        
        if apoc_count > 0:
            print("APOC is installed! 👍")
            
            # Check for specific APOC procedure needed for GraphRAG
            result = session.run("""
                CALL dbms.procedures()
                YIELD name
                WHERE name = 'apoc.meta.data'
                RETURN count(name) > 0 as hasMetaData
            """)
            has_meta_data = result.single()["hasMetaData"]
            
            if has_meta_data:
                print("apoc.meta.data procedure is available! GraphRAG should work.")
            else:
                print("WARNING: apoc.meta.data procedure not found, which is needed for GraphRAG.")
                print("Make sure APOC is properly configured.")
        else:
            print("APOC is NOT installed! You need to install it in Neo4j Desktop.")
            print("Go to your database in Neo4j Desktop -> Plugins -> Install APOC")
    
    driver.close()

if __name__ == "__main__":
    check_apoc() 