"""
Import CoinAPI Data to Neo4j

This script imports CoinAPI indexes data into the Neo4j knowledge graph
"""

import os
import sys
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# Import Neo4j connector
from modules.graph_builder.neo4j_connector import Neo4jConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

def fetch_coinapi_data():
    """Fetch data from CoinAPI"""
    coinapi_data = []
    try:
        coinapi_key = os.getenv("COINAPI_KEY")
        if not coinapi_key:
            logging.warning("No CoinAPI key found in environment variables, using mock data")
            return get_mock_coinapi_data()
        
        url = "https://rest.coinapi.io/v1/indexes"
        headers = {"X-CoinAPI-Key": coinapi_key}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            all_indexes = response.json()
            logging.info(f"Successfully fetched {len(all_indexes)} CoinAPI indexes")
            return all_indexes
        elif response.status_code == 401:
            logging.error("CoinAPI authentication failed - invalid API key")
        elif response.status_code == 429:
            logging.error("CoinAPI rate limit exceeded")
        else:
            logging.error(f"Error fetching CoinAPI data: Status code {response.status_code}")
    except requests.exceptions.Timeout:
        logging.error("Timeout while fetching CoinAPI data")
    except requests.exceptions.ConnectionError:
        logging.error("Connection error while fetching CoinAPI data")
    except Exception as e:
        logging.error(f"Error fetching CoinAPI data: {str(e)}")
    
    # Return mock data if real data couldn't be fetched
    return get_mock_coinapi_data()

def get_mock_coinapi_data():
    """Get mock CoinAPI data for testing"""
    logging.info("Using mock CoinAPI data")
    return [
        {
            "index_id": "MVDA",
            "name": "CryptoCompare Digital Asset 10 Index",
            "description": "The MVDA is designed to track the performance of the 10 largest digital assets in the world, as measured and weighted by market cap. The index is calculated in USD.",
            "last_value": 4123.84,
            "asset_pairs": ["BTC/USD", "ETH/USD", "XRP/USD", "BCH/USD", "LTC/USD"]
        },
        {
            "index_id": "MVIS",
            "name": "MVIS CryptoCompare Digital Assets 100 Index",
            "description": "A modified market cap-weighted index which tracks the performance of the 100 largest digital assets.",
            "last_value": 2876.52,
            "asset_pairs": ["BTC/USD", "ETH/USD", "ADA/USD", "DOT/USD", "XRP/USD"]
        },
        {
            "index_id": "BITX",
            "name": "Bitwise 10 Large Cap Crypto Index",
            "description": "An index of the 10 largest cryptocurrency assets by market capitalization, weighted by market cap.",
            "last_value": 3542.18,
            "asset_pairs": ["BTC/USD", "ETH/USD", "SOL/USD"]
        },
        {
            "index_id": "BLCX",
            "name": "Bloomberg Galaxy Crypto Index",
            "description": "Designed to measure the performance of the largest cryptocurrencies traded in USD.",
            "last_value": 1985.73,
            "asset_pairs": ["BTC/USD", "ETH/USD", "XRP/USD", "BCH/USD"]
        },
        {
            "index_id": "DEFI",
            "name": "CoinDesk DeFi Index",
            "description": "Tracks the performance of decentralized financial assets across the market.",
            "last_value": 845.29,
            "asset_pairs": ["UNI/USD", "AAVE/USD", "COMP/USD", "SNX/USD", "MKR/USD"]
        }
    ]

def import_coinapi_data_to_neo4j(indexes):
    """Import CoinAPI indexes data into Neo4j"""
    connector = Neo4jConnector()
    if not connector.connect():
        logging.error("Failed to connect to Neo4j")
        return False
    
    timestamp = datetime.now().strftime("%Y-%m-%d")
    
    # Create the CoinAPIIndex node type if it doesn't exist (schema)
    schema_query = """
    CREATE CONSTRAINT coinapi_index_id IF NOT EXISTS
    FOR (index:CoinAPIIndex)
    REQUIRE index.index_id IS UNIQUE
    """
    try:
        connector.run_query(schema_query)
        logging.info("Created schema constraints for CoinAPIIndex")
    except Exception as e:
        logging.error(f"Error creating schema constraints: {e}")
    
    # Import each index
    successful_imports = 0
    for index in indexes:
        # Skip if missing required fields
        if not index.get("index_id") or not index.get("name"):
            continue
        
        # Import the index
        try:
            # Create the CoinAPIIndex node
            query = """
            MERGE (i:CoinAPIIndex {index_id: $index_id})
            SET i.name = $name,
                i.description = $description,
                i.last_value = $last_value,
                i.update_date = $update_date
            """
            
            params = {
                "index_id": index.get("index_id"),
                "name": index.get("name"),
                "description": index.get("description", ""),
                "last_value": index.get("last_value", 0),
                "update_date": timestamp
            }
            
            connector.run_query(query, params)
            
            # Create asset pair relationships
            asset_pairs = index.get("asset_pairs", [])
            for pair in asset_pairs:
                # Extract crypto symbols from pair (like BTC/USD -> BTC)
                parts = pair.split("/")
                if len(parts) >= 1:
                    crypto_symbol = parts[0]
                    
                    # Connect to any matching Cryptocurrency nodes
                    crypto_query = """
                    MATCH (i:CoinAPIIndex {index_id: $index_id})
                    MATCH (c:Cryptocurrency)
                    WHERE c.symbol = $symbol OR toLower(c.name) = toLower($symbol)
                    MERGE (i)-[r:INCLUDES_CRYPTO]->(c)
                    SET r.pair = $pair
                    """
                    
                    crypto_params = {
                        "index_id": index.get("index_id"),
                        "symbol": crypto_symbol,
                        "pair": pair
                    }
                    
                    connector.run_query(crypto_query, crypto_params)
            
            # Add index data as an Entity node for GraphRAG to use
            entity_query = """
            MATCH (i:CoinAPIIndex {index_id: $index_id})
            WITH i
            MERGE (e:Entity {id: 'coinapi_' + i.index_id})
            SET e.name = i.name,
                e.type = 'CoinAPIIndex',
                e.description = i.description,
                e.value = toString(i.last_value),
                e.timestamp = i.update_date
            MERGE (e)-[:REPRESENTS]->(i)
            """
            
            entity_params = {
                "index_id": index.get("index_id")
            }
            
            connector.run_query(entity_query, entity_params)
            
            successful_imports += 1
        except Exception as e:
            logging.error(f"Error importing index {index.get('index_id')}: {e}")
    
    connector.close()
    logging.info(f"Successfully imported {successful_imports} out of {len(indexes)} CoinAPI indexes")
    return successful_imports > 0

def main():
    """Main function to fetch and import CoinAPI data"""
    print("=== Importing CoinAPI Indexes to Neo4j ===")
    indexes = fetch_coinapi_data()
    if indexes:
        if import_coinapi_data_to_neo4j(indexes):
            print("CoinAPI data import completed successfully")
        else:
            print("CoinAPI data import failed")
    else:
        print("No CoinAPI data to import")

if __name__ == "__main__":
    main() 