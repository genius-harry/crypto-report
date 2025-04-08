# Neo4j GraphRAG Setup Guide

This guide will help you set up Neo4j locally and run a demonstration of a Graph-based Retrieval Augmented Generation (GraphRAG) system for crypto data.

## Prerequisites

- macOS 10.10+ (this guide is for macOS, but Neo4j supports Windows and Linux as well)
- Python 3.8+
- Pip package manager
- OpenAI API key (added to your `.env` file)

## 1. Install Neo4j Desktop

### Download

1. Visit [Neo4j Download Page](https://neo4j.com/download/)
2. Fill out the form to download Neo4j Desktop for macOS
3. Wait for the `.dmg` file to download

### Install

1. Find the `.dmg` file in your Downloads folder and double-click it
2. Drag the Neo4j Desktop icon to your Applications folder
3. Open Neo4j Desktop from your Applications folder

## 2. Set Up a Neo4j Database

1. Open Neo4j Desktop
2. Create a new project (e.g., "CryptoGraphRAG")
3. Within your project, click "Add Database"
4. Choose "Create a Local Database"
5. Name your database (e.g., "crypto-graph")
6. Set a password (remember this for later)
7. Click "Create" to create the database
8. Start the database by clicking the "Start" button

## 3. Configure the Python Script

1. Open the `neo4j_graphrag_demo.py` file in your editor
2. Update the Neo4j connection parameters:
   ```python
   NEO4J_URI = "bolt://localhost:7687"  # This is usually the default URI
   NEO4J_USERNAME = "neo4j"             # Default username
   NEO4J_PASSWORD = "your-password"     # Replace with the password you set in step 2.6
   ```
3. Make sure your `.env` file contains your OpenAI API key:
   ```
   OPENAI_API_KEY=your-openai-api-key
   ```

## 4. Run the GraphRAG Demo

1. Open a terminal in the project directory
2. Make sure Neo4j database is running in Neo4j Desktop
3. Run the demo script:
   ```bash
   python neo4j_graphrag_demo.py
   ```
4. The script will:
   - Connect to your Neo4j database
   - Create a sample crypto knowledge graph
   - Set up a GraphRAG system using LangChain and Neo4j
   - Run sample queries to demonstrate the system

## 5. Understanding the Graph Schema

The demo creates a simple crypto knowledge graph with the following structure:

- Nodes:
  - `Cryptocurrency`: Bitcoin, Ethereum, Solana
  - `Person`: Satoshi Nakamoto, Vitalik Buterin
  - `Document`: Bitcoin and Ethereum whitepapers
  - `Concept`: Proof of Work, Proof of Stake

- Relationships:
  - `CREATED`: Person created a cryptocurrency
  - `AUTHORED`: Person authored a document
  - `DESCRIBES`: Document describes a cryptocurrency
  - `USES`: Cryptocurrency uses a consensus mechanism
  - `RELATED_TO`: Connection between cryptocurrencies

## 6. Exploring with Neo4j Browser

1. In Neo4j Desktop, click on "Open" with the three dots next to your running database
2. Select "Open with Neo4j Browser"
3. Try some Cypher queries:
   ```cypher
   // View all nodes
   MATCH (n) RETURN n
   
   // View relationships between cryptocurrencies
   MATCH (c1:Cryptocurrency)-[r]-(c2:Cryptocurrency) RETURN c1, r, c2
   
   // Find the creator of Bitcoin
   MATCH (p:Person)-[:CREATED]->(c:Cryptocurrency {name: 'Bitcoin'}) RETURN p, c
   ```

## 7. Expanding the GraphRAG System

To expand on this demo for a full-fledged GraphRAG system:

1. Import more comprehensive crypto data
2. Add vector embeddings for text content
3. Create more complex relationship types
4. Implement hybrid search (graph + vector)
5. Connect to live data sources

## Troubleshooting

- **Connection Issues**: Make sure Neo4j is running and the URI, username, and password are correct
- **Port Conflicts**: If port 7687 is already in use, configure Neo4j to use a different port
- **Python Dependencies**: Make sure all required packages are installed

## Resources

- [Neo4j Documentation](https://neo4j.com/docs/)
- [Neo4j with LangChain](https://python.langchain.com/docs/integrations/providers/neo4j/)
- [Neo4j GraphRAG](https://neo4j.com/docs/graph-data-science/current/graph-rag/) 