"""
Neo4j GraphRAG Final Demo

This script demonstrates how to use Neo4j to build a Graph-based Retrieval Augmented Generation system
using the correct LangChain APIs.
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_neo4j import Neo4jGraph
from langchain_neo4j import GraphCypherQAChain

# Load environment variables
load_dotenv()

# Neo4j connection parameters
NEO4J_URI = "bolt://localhost:7687"  # Default Neo4j URI
NEO4J_USERNAME = "neo4j"             # Default username
NEO4J_PASSWORD = "Yaoyiran20061111"  # Your password

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

def setup_graphrag():
    """Set up a GraphRAG system using LangChain and Neo4j."""
    # Initialize OpenAI components
    llm = ChatOpenAI(temperature=0)
    
    try:
        # Connect to Neo4j using LangChain's Neo4jGraph
        graph = Neo4jGraph(
            url=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database="neo4j"
        )
        
        # Create a graph-based QA chain with security flag
        chain = GraphCypherQAChain.from_llm(
            llm=llm,
            graph=graph,
            verbose=True,
            allow_dangerous_requests=True  # Enable this flag since we're in a controlled environment
        )
        
        return chain
    except Exception as e:
        print(f"Error setting up GraphRAG chain: {e}")
        
        # Use fallback approach with direct Cypher generation
        return create_fallback_chain(llm)

def create_fallback_chain(llm):
    """Create a fallback chain using direct Cypher generation."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    def query_handler(question):
        print("\nUsing fallback approach with direct Cypher generation")
        
        # Generate a Cypher query using the LLM
        cypher_prompt = f"""
        Given this question: '{question}'
        
        Write a Cypher query to answer it using a graph with these entities and relationships:
        - (Person)-[:CREATED]->(Cryptocurrency)
        - (Person)-[:AUTHORED]->(Document)
        - (Document)-[:DESCRIBES]->(Cryptocurrency)
        - (Cryptocurrency)-[:USES]->(Concept)
        - (Cryptocurrency)-[:RELATED_TO]->(Cryptocurrency)
        
        Return only the Cypher query, nothing else.
        """
        
        cypher_response = llm.invoke(cypher_prompt)
        cypher_query = cypher_response.content.strip()
        
        print(f"Generated Cypher query: {cypher_query}")
        
        # Execute the query
        with driver.session() as session:
            try:
                result = session.run(cypher_query)
                records = [dict(record) for record in result]
                
                # Format results
                results_str = "\n".join([str(r) for r in records])
                
                # Generate answer using LLM
                answer_prompt = f"""
                Question: {question}
                
                Query results:
                {results_str}
                
                Please provide a clear, concise answer based on the query results.
                """
                
                answer = llm.invoke(answer_prompt)
                return {"result": answer.content}
                
            except Exception as query_error:
                print(f"Error executing query: {query_error}")
                return {"result": f"Error executing query: {query_error}"}
    
    return query_handler

def query_graph(chain, question):
    """Query the GraphRAG system with a question."""
    # Check if we're using the fallback approach
    if callable(chain) and not hasattr(chain, 'invoke'):
        # Fallback chain is just a function
        return chain(question)
    else:
        # Standard chain with invoke method
        response = chain.invoke({"query": question})
        return response

def main():
    """Main function to demonstrate Neo4j GraphRAG setup."""
    print("Neo4j GraphRAG Final Demo")
    print("=======================\n")
    
    # Connect to Neo4j
    driver = connect_to_neo4j()
    if not driver:
        print("Failed to connect to Neo4j. Please make sure Neo4j is running with the correct credentials.")
        return
    
    # Create sample data
    create_sample_graph(driver)
    
    # Setup GraphRAG
    print("\nSetting up GraphRAG system...")
    chain = setup_graphrag()
    
    # Demo queries
    print("\nQuerying the GraphRAG system:")
    demo_questions = [
        "Who created Bitcoin?",
        "What consensus mechanism does Ethereum use?",
        "How are Ethereum and Solana related?"
    ]
    
    for question in demo_questions:
        print(f"\nQuestion: {question}")
        try:
            response = query_graph(chain, question)
            print(f"Answer: {response['result']}")
        except Exception as e:
            print(f"Error querying graph: {e}")
    
    # Close connection
    driver.close()
    print("\nNeo4j connection closed.")

if __name__ == "__main__":
    main() 