"""
Crypto QA Demo

This script demonstrates how to use Neo4j with LLMs for cryptocurrency knowledge querying
without relying on complex GraphRAG components.
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# Neo4j connection parameters
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "Yaoyiran20061111"

# OpenAI API key is loaded from .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def connect_to_neo4j():
    """Establish connection to Neo4j database."""
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

def query_crypto_knowledge(question, driver, llm):
    """Query the crypto knowledge graph using LLM-generated Cypher."""
    # Step 1: Generate a Cypher query based on the user question
    cypher_prompt = f"""
    Given this user question: '{question}'
    
    Write a Cypher query to get the answer from a Neo4j graph with these nodes and relationships:
    
    Nodes:
    - (c:Cryptocurrency) with properties: name, symbol, price
    - (p:Person) with properties: name
    - (d:Document) with properties: title, year
    - (c:Concept) with properties: name
    
    Relationships:
    - (Person)-[:CREATED]->(Cryptocurrency)
    - (Person)-[:AUTHORED]->(Document)
    - (Document)-[:DESCRIBES]->(Cryptocurrency)
    - (Cryptocurrency)-[:USES]->(Concept)
    - (Cryptocurrency)-[:RELATED_TO]->(Cryptocurrency)
    
    Return ONLY the Cypher query, nothing else.
    """
    
    response = llm.invoke(cypher_prompt)
    cypher_query = response.content.strip()
    
    print(f"\nGenerated Cypher query: {cypher_query}")
    
    # Step 2: Execute the query against Neo4j
    with driver.session() as session:
        try:
            result = session.run(cypher_query)
            records = [record.data() for record in result]
            print(f"\nQuery results: {records}")
            
            if not records:
                return "I couldn't find information to answer that question in the knowledge graph."
            
            # Step 3: Format the results for the LLM
            results_text = "\n".join([str(record) for record in records])
            
            # Step 4: Generate a natural language answer
            answer_prompt = f"""
            Question: {question}
            
            Database query results:
            {results_text}
            
            Based on these results, provide a clear, concise answer to the question.
            """
            
            answer_response = llm.invoke(answer_prompt)
            return answer_response.content.strip()
            
        except Exception as e:
            print(f"Error executing query: {e}")
            return f"I encountered an error trying to answer your question: {str(e)}"

def main():
    """Main function to demonstrate Neo4j with LLM for crypto QA."""
    print("Crypto QA Demo")
    print("==============\n")
    
    # Initialize LLM
    llm = ChatOpenAI(temperature=0)
    
    # Connect to Neo4j
    driver = connect_to_neo4j()
    if not driver:
        print("Failed to connect to Neo4j. Please make sure Neo4j is running with the correct credentials.")
        return
    
    # Create sample data
    create_sample_graph(driver)
    
    # Demo queries
    print("\nDemonstrating crypto knowledge queries:")
    demo_questions = [
        "Who created Bitcoin?",
        "What consensus mechanism does Ethereum use?",
        "How are Ethereum and Solana related?"
    ]
    
    for question in demo_questions:
        print(f"\nQuestion: {question}")
        answer = query_crypto_knowledge(question, driver, llm)
        print(f"Answer: {answer}")
    
    # Close connection
    driver.close()
    print("\nNeo4j connection closed.")

if __name__ == "__main__":
    main() 