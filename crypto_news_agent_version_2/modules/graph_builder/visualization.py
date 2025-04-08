"""
Graph Visualization Module

This module handles creating visualizations of the Neo4j graph.
"""

import os
import json
import matplotlib.pyplot as plt
import networkx as nx
from pyvis.network import Network
from typing import Dict, List, Any, Optional

from .neo4j_connector import Neo4jConnector

def create_crypto_network(connector: Neo4jConnector, output_dir: str = "static") -> str:
    """
    Create cryptocurrency network visualization.
    
    Args:
        connector: Neo4j connector
        output_dir: Directory to save the visualization
        
    Returns:
        Path to the created visualization
    """
    try:
        # Get cryptocurrencies
        nodes_query = """
                MATCH (c:Cryptocurrency)
                RETURN id(c) AS id, c.name AS name, c.symbol AS symbol, 
                       size([(c)-[:MENTIONED_IN]->(a:Article) | a]) AS article_count
            """
        nodes_result = connector.run_query(nodes_query)
        
        # Get relationships with higher strength threshold to filter out weak connections
        edges_query = """
                MATCH (c1:Cryptocurrency)-[r:RELATED_TO]-(c2:Cryptocurrency)
                WHERE r.common_articles >= 5
                RETURN id(c1) AS source, id(c2) AS target, r.common_articles AS weight
            """
        edges_result = connector.run_query(edges_query)
        
        if not nodes_result:
            print("No cryptocurrency nodes found")
            return ""
        
        # Create network
        net = Network(height="600px", width="100%", notebook=False, 
                      bgcolor="#222222", font_color="white")
        
        # Add nodes with smaller sizes
        for record in nodes_result:
            # Calculate size based on article count, but keep it small
            size = 15 + min(15, record.get("article_count", 1))
            net.add_node(record["id"], 
                         label=f"{record['name']} ({record['symbol']})", 
                         title=f"{record['name']} ({record['symbol']}) - {record.get('article_count', 0)} articles",
                         color="#4FADE6",
                         size=size)
        
        # Add edges
        for record in edges_result:
            width = 1 + min(3, record["weight"] / 3)  # Scale width based on weight, but cap it smaller
            net.add_edge(record["source"], record["target"], 
                         value=record["weight"], 
                         title=f"Common articles: {record['weight']}",
                         width=width)
        
        # Set physics layout
        net.set_options("""
        {
          "physics": {
            "forceAtlas2Based": {
              "gravitationalConstant": -50,
              "centralGravity": 0.01,
              "springLength": 100,
              "springConstant": 0.05
            },
            "maxVelocity": 50,
            "solver": "forceAtlas2Based",
            "timestep": 0.35,
            "stabilization": {
              "enabled": true,
              "iterations": 1000
            }
          }
        }
        """)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save visualization
        output_path = os.path.join(output_dir, "crypto_network.html")
        net.save_html(output_path)
        
        print(f"Created cryptocurrency network visualization: {output_path}")
        return output_path
    
    except Exception as e:
        print(f"Error creating cryptocurrency network: {e}")
        return ""

def create_topic_network(connector: Neo4jConnector, output_dir: str = "static") -> str:
    """
    Create topic network visualization.
    
    Args:
        connector: Neo4j connector
        output_dir: Directory to save the visualization
        
    Returns:
        Path to the created visualization
    """
    try:
        # Get topics with article counts
        nodes_query = """
                MATCH (t:Topic)
                RETURN id(t) AS id, t.name AS name,
                       size([(t)<-[:HAS_TOPIC]-(a:Article) | a]) AS article_count
            """
        nodes_result = connector.run_query(nodes_query)
        
        # Get relationships with strength threshold
        edges_query = """
                MATCH (t1:Topic)-[r:RELATED_TO]-(t2:Topic)
                WHERE r.common_articles >= 3
                RETURN id(t1) AS source, id(t2) AS target, r.common_articles AS weight
            """
        edges_result = connector.run_query(edges_query)
        
        if not nodes_result:
            print("No topic nodes found")
            return ""
        
        # Create network
        net = Network(height="600px", width="100%", notebook=False, 
                      bgcolor="#222222", font_color="white")
        
        # Add nodes with smaller sizes
        for record in nodes_result:
            # Calculate size based on article count, but keep it small
            size = 15 + min(15, record.get("article_count", 1))
            net.add_node(record["id"], 
                         label=record["name"], 
                         title=f"{record['name']} - {record.get('article_count', 0)} articles",
                         color="#E6A34F",
                         size=size)
        
        # Add edges
        for record in edges_result:
            width = 1 + min(3, record["weight"] / 3)  # Scale width based on weight, but cap it smaller
            net.add_edge(record["source"], record["target"], 
                         value=record["weight"], 
                         title=f"Common articles: {record['weight']}",
                         width=width)
        
        # Set physics layout
        net.set_options("""
        {
          "physics": {
            "forceAtlas2Based": {
              "gravitationalConstant": -50,
              "centralGravity": 0.01,
              "springLength": 100,
              "springConstant": 0.05
            },
            "maxVelocity": 50,
            "solver": "forceAtlas2Based",
            "timestep": 0.35,
            "stabilization": {
              "enabled": true,
              "iterations": 1000
            }
          }
        }
        """)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save visualization
        output_path = os.path.join(output_dir, "topic_network.html")
        net.save_html(output_path)
        
        print(f"Created topic network visualization: {output_path}")
        return output_path
    
    except Exception as e:
        print(f"Error creating topic network: {e}")
        return ""

def create_d3_data(connector: Neo4jConnector, output_dir: str = "static") -> str:
    """
    Create D3.js compatible JSON data for interactive visualization.
    
    Args:
        connector: Neo4j connector
        output_dir: Directory to save the data
        
    Returns:
        Path to the generated JSON file
    """
    if not connector.driver:
        if not connector.connect():
            return ""
    
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        with connector.driver.session() as session:
            # Get all nodes
            crypto_result = session.run("""
                MATCH (c:Cryptocurrency)
                RETURN id(c) AS id, c.name AS name, c.symbol AS symbol, 'Cryptocurrency' AS type
            """)
            
            topic_result = session.run("""
                MATCH (t:Topic)
                RETURN id(t) AS id, t.name AS name, 'Topic' AS type
            """)
            
            article_result = session.run("""
                MATCH (a:Article)
                RETURN id(a) AS id, a.title AS name, 'Article' AS type
                LIMIT 15  // Limit to avoid overcrowding
            """)
            
            # Create nodes list
            nodes = []
            id_mapping = {}  # Map Neo4j IDs to array indices
            
            # Add cryptocurrency nodes (group 1)
            idx = 0
            for record in crypto_result:
                id_mapping[record["id"]] = idx
                nodes.append({
                    "id": idx,
                    "name": record["name"],
                    "type": record["type"],
                    "symbol": record["symbol"],
                    "group": 1
                })
                idx += 1
            
            # Add topic nodes (group 2)
            for record in topic_result:
                id_mapping[record["id"]] = idx
                nodes.append({
                    "id": idx,
                    "name": record["name"],
                    "type": record["type"],
                    "group": 2
                })
                idx += 1
            
            # Add article nodes (group 3)
            for record in article_result:
                id_mapping[record["id"]] = idx
                nodes.append({
                    "id": idx,
                    "name": record["name"],
                    "type": record["type"],
                    "group": 3
                })
                idx += 1
            
            # Get relationships
            rel_result = session.run("""
                MATCH (n1)-[r]-(n2)
                RETURN id(n1) AS source, id(n2) AS target, type(r) AS type
                LIMIT 150  // Limit to avoid overcrowding
            """)
            
            # Create links list
            links = []
            for record in rel_result:
                source_id = record["source"]
                target_id = record["target"]
                
                # Skip if source or target is not in our nodes list
                if source_id not in id_mapping or target_id not in id_mapping:
                    continue
                
                links.append({
                    "source": id_mapping[source_id],
                    "target": id_mapping[target_id],
                    "type": record["type"],
                    "value": 1
                })
        
        # Create the final graph data
        graph_data = {
            "nodes": nodes,
            "links": links
        }
        
        # Save as JSON
        json_path = os.path.join(output_dir, "graph_data.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        
        print(f"Created D3.js compatible graph data: {json_path}")
        return json_path
    
    except Exception as e:
        print(f"Error creating D3.js data: {e}")
        return ""

def create_all_visualizations(connector: Neo4jConnector, output_dir: str = "static") -> Dict[str, str]:
    """
    Create all visualizations for the graph.
    
    Args:
        connector: Neo4j connector
        output_dir: Directory to save the visualizations
        
    Returns:
        Dictionary of visualization paths
    """
    print("\nCreating graph visualizations...")
    
    vis_paths = {}
    
    # Create cryptocurrency network
    crypto_path = create_crypto_network(connector, output_dir)
    if crypto_path:
        vis_paths["crypto_network"] = crypto_path
    
    # Create topic network
    topic_path = create_topic_network(connector, output_dir)
    if topic_path:
        vis_paths["topic_network"] = topic_path
    
    # Create D3.js data
    d3_path = create_d3_data(connector, output_dir)
    if d3_path:
        vis_paths["d3_data"] = d3_path
    
    print("All visualizations created successfully!")
    return vis_paths 