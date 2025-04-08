"""
Crypto GraphRAG Query System

This script demonstrates how to query the Neo4j GraphRAG system for crypto insights,
combining graph traversal with vector similarity search.
"""

import os
import argparse
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import GraphCypherQAChain
from langchain_community.graphs import Neo4jGraph
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Load environment variables
load_dotenv()

# Neo4j connection parameters - update these after installing Neo4j Desktop
NEO4J_URI = "bolt://localhost:7687"  # Default Neo4j URI
NEO4J_USERNAME = "neo4j"             # Default username
NEO4J_PASSWORD = "Yaoyiran20061111"  # Updated password

# OpenAI API key for embeddings and LLM
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

def setup_graphrag_chain():
    """Set up the GraphRAG chain using LangChain and Neo4j."""
    # Initialize the language model
    llm = ChatOpenAI(temperature=0)
    
    # Initialize embeddings
    embeddings = OpenAIEmbeddings()
    
    # Connect to Neo4j graph
    graph = Neo4jGraph(
        url=NEO4J_URI,
        username=NEO4J_USERNAME,
        password=NEO4J_PASSWORD
    )
    
    # Create a GraphQA chain
    graphqa_chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        verbose=True,
    )
    
    # Create a prompt template for the final response
    response_prompt = PromptTemplate.from_template(
        """
        Based on the graph database query results and article information, provide an insightful answer to the following question:
        
        Question: {question}
        
        Graph Query Results: {graphqa_result}
        
        Related Articles: {article_content}
        
        Provide a comprehensive answer using both the structured graph data and unstructured article text.
        Focus on accuracy and cite your sources where appropriate.
        """
    )
    
    # Define the query function for vector search to get related articles
    def get_related_articles(query):
        # Generate embedding for the query
        query_embedding = embeddings.embed_query(query)
        
        # Query Neo4j for related articles using vector similarity
        with GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD)).session() as session:
            # Check if vector search is available
            has_vector = session.run("""
                CALL dbms.procedures() 
                YIELD name 
                WHERE name = 'db.index.vector.queryNodes' 
                RETURN count(*) > 0 AS hasVectorSearch
            """).single()["hasVectorSearch"]
            
            if has_vector:
                # Use vector search
                result = session.run("""
                    CALL db.index.vector.queryNodes('articleEmbeddings', $embedding, 3)
                    YIELD node, score
                    RETURN node.title AS title, node.summary AS summary, node.date AS date, score
                    LIMIT 3
                """, {"embedding": query_embedding})
            else:
                # Fallback to regular search
                result = session.run("""
                    MATCH (a:Article)
                    WHERE a.title CONTAINS $query OR a.content CONTAINS $query
                    RETURN a.title AS title, a.summary AS summary, a.date AS date, 1.0 AS score
                    LIMIT 3
                """, {"query": query})
            
            articles = [f"Title: {record['title']}\nDate: {record['date']}\nSummary: {record['summary']}\nRelevance: {record['score']}\n"
                     for record in result]
            
            return "\n".join(articles) if articles else "No relevant articles found."
    
    # Create the full chain
    chain = (
        {"question": RunnablePassthrough(), 
         "graphqa_result": lambda x: graphqa_chain.invoke({"query": x}),
         "article_content": get_related_articles}
        | response_prompt
        | llm
        | StrOutputParser()
    )
    
    return chain

def query_graph_for_crypto_insights(question, mode="standard"):
    """Query the Neo4j graph for crypto insights."""
    print(f"Question: {question}")
    print("Processing...")
    
    # Connect to Neo4j
    driver = connect_to_neo4j()
    if not driver:
        return "Failed to connect to Neo4j database. Please check your connection parameters."
    
    try:
        if mode == "direct":
            # Direct Cypher query mode for advanced users
            with driver.session() as session:
                result = session.run(question)
                records = [record.data() for record in result]
                driver.close()
                return records
        else:
            # Standard GraphRAG mode
            chain = setup_graphrag_chain()
            response = chain.invoke(question)
            driver.close()
            return response
    except Exception as e:
        driver.close()
        return f"Error processing your query: {str(e)}"

def run_sample_queries():
    """Run some sample queries to demonstrate the system."""
    sample_questions = [
        "What are the recent trends in Bitcoin prices?",
        "How is the market sentiment about Ethereum?",
        "Which cryptocurrency has had the most positive news coverage in the last month?",
        "What are the main concerns about cryptocurrency regulation based on recent news?",
        "How are Bitcoin and Ethereum related according to recent articles?"
    ]
    
    for question in sample_questions:
        print("\n" + "="*80)
        print(f"Sample Question: {question}")
        print("="*80)
        
        answer = query_graph_for_crypto_insights(question)
        print("\nAnswer:")
        print(answer)
        print("\n" + "="*80)
        
        # Ask for user input to continue
        input("Press Enter to continue to the next question...")

def main():
    """Main function for the Crypto GraphRAG Query System."""
    parser = argparse.ArgumentParser(description="Query the Crypto GraphRAG system.")
    parser.add_argument("--question", type=str, help="Question to ask the system")
    parser.add_argument("--mode", choices=["standard", "direct"], default="standard",
                        help="Query mode: standard (natural language) or direct (Cypher)")
    parser.add_argument("--samples", action="store_true", help="Run sample questions")
    
    args = parser.parse_args()
    
    print("Crypto GraphRAG Query System")
    print("===========================\n")
    
    if args.samples:
        run_sample_queries()
    elif args.question:
        answer = query_graph_for_crypto_insights(args.question, args.mode)
        print("\nAnswer:")
        print(answer)
    else:
        # Interactive mode
        print("Enter your questions about cryptocurrencies. Type 'exit' to quit.")
        while True:
            question = input("\nYour question: ")
            if question.lower() in ("exit", "quit", "q"):
                break
                
            answer = query_graph_for_crypto_insights(question)
            print("\nAnswer:")
            print(answer)

if __name__ == "__main__":
    main() 