"""
Query Crypto News GraphRAG

This script allows querying the crypto news knowledge graph in Neo4j
using natural language questions.
"""

import os
import argparse
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph
from langchain_neo4j import GraphCypherQAChain

# Load environment variables
load_dotenv()

# Neo4j connection parameters
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "Yaoyiran20061111"

# OpenAI API key from .env file
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
        return driver
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        return None

def setup_graphrag():
    """Set up the GraphRAG system."""
    # Initialize LLM
    llm = ChatOpenAI(temperature=0)
    
    try:
        # Connect to Neo4j
        graph = Neo4jGraph(
            url=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database="neo4j"
        )
        
        # Create QA chain
        chain = GraphCypherQAChain.from_llm(
            llm=llm,
            graph=graph,
            verbose=True,
            allow_dangerous_requests=True
        )
        
        return chain
    except Exception as e:
        print(f"Error setting up GraphRAG: {e}")
        return None

def generate_direct_cypher(question):
    """Generate a Cypher query directly using LLM for complex questions."""
    llm = ChatOpenAI(temperature=0)
    
    prompt = f"""
    Given this question about cryptocurrency news: '{question}'
    
    Write a Cypher query to answer it using a Neo4j graph with the following schema:
    
    Nodes:
    - (Article) with properties: title, url, snippet, published_date, searched_at, search_engine
    - (Source) with properties: name
    - (Cryptocurrency) with properties: name, symbol
    - (Query) with properties: text
    
    Relationships:
    - (Article)-[:FROM]->(Source)
    - (Article)-[:MENTIONS]->(Cryptocurrency)
    - (Article)-[:FOUND_BY]->(Query)
    - (Cryptocurrency)-[:RELATED_TO]-(Cryptocurrency) with property: common_articles (count of articles mentioning both)
    
    Return only the Cypher query, nothing else.
    """
    
    response = llm.invoke(prompt)
    return response.content.strip()

def query_graph(question, mode="graphrag"):
    """Query the crypto news knowledge graph."""
    print(f"Question: {question}")
    print("Processing...")
    
    # Connect to Neo4j
    driver = connect_to_neo4j()
    if not driver:
        return "Failed to connect to Neo4j database."
    
    try:
        if mode == "direct":
            # Direct Cypher query approach
            cypher_query = generate_direct_cypher(question)
            print(f"\nGenerated Cypher query:\n{cypher_query}")
            
            with driver.session() as session:
                result = session.run(cypher_query)
                records = [record.data() for record in result]
            
            driver.close()
            
            if not records:
                return "No results found for your query."
            
            # Format the results
            formatted_results = "\n".join([str(record) for record in records])
            
            # Summarize with LLM
            llm = ChatOpenAI(temperature=0)
            summary_prompt = f"""
            Question: {question}
            
            Query results from cryptocurrency news database:
            {formatted_results}
            
            Please provide a clear, comprehensive answer based only on these results.
            """
            
            summary = llm.invoke(summary_prompt)
            return summary.content
            
        else:
            # GraphRAG approach
            chain = setup_graphrag()
            if not chain:
                driver.close()
                return "Failed to set up GraphRAG system."
            
            response = chain.invoke({"query": question})
            driver.close()
            return response["result"]
            
    except Exception as e:
        driver.close()
        return f"Error processing your query: {str(e)}"

def demo_questions():
    """Run a series of demo questions."""
    questions = [
        "What are the most mentioned cryptocurrencies in the news?",
        "How are Bitcoin and Ethereum related based on the news?",
        "Which news sources talk about cryptocurrency the most?",
        "What are some recent developments about XRP?",
        "Are there any news about cryptocurrency regulations?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'-'*80}")
        print(f"Demo Question {i}: {question}")
        print(f"{'-'*80}")
        
        answer = query_graph(question)
        print(f"\nAnswer: {answer}")
        
        input("\nPress Enter to continue to the next question...")

def interactive_mode():
    """Run in interactive mode."""
    print("Crypto News Query System")
    print("Enter your questions about cryptocurrency news. Type 'exit' to quit.")
    
    while True:
        question = input("\nYour question: ")
        if question.lower() in ("exit", "quit", "q"):
            break
            
        mode = "graphrag"
        if question.lower().startswith("direct:"):
            mode = "direct"
            question = question[7:].strip()
            
        answer = query_graph(question, mode)
        print(f"\nAnswer: {answer}")

def main():
    """Main function for the Crypto News Query system."""
    parser = argparse.ArgumentParser(description="Query the Crypto News GraphRAG system.")
    parser.add_argument("--question", type=str, help="Question to ask")
    parser.add_argument("--mode", choices=["graphrag", "direct"], default="graphrag",
                      help="Query mode: graphrag (natural language) or direct (Cypher)")
    parser.add_argument("--demo", action="store_true", help="Run demo questions")
    
    args = parser.parse_args()
    
    print("Crypto News GraphRAG Query System")
    print("================================\n")
    
    if args.demo:
        demo_questions()
    elif args.question:
        answer = query_graph(args.question, args.mode)
        print(f"\nAnswer: {answer}")
    else:
        interactive_mode()

if __name__ == "__main__":
    main() 