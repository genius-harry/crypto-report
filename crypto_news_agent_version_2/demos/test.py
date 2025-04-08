from neo4j import GraphDatabase
import os
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

def test_connection():
    with driver.session() as session:
        result = session.run("""
        CREATE (t:TestNode {message: 'Connection successful!'})
        RETURN t.message AS message
        """)
        print("Test result:", result.single()["message"])

test_connection()
driver.close()
