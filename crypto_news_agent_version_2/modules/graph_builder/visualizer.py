def create_cryptocurrency_network_visualization(graph_connector, output_path="static/crypto_network.html"):
    """Create cryptocurrency network visualization."""
    # Query for all cryptocurrencies
    result = graph_connector.query('''
                MATCH (c:Cryptocurrency)
                RETURN id(c) AS id, c.name AS name, c.symbol AS symbol
            ''')
    
    # Get relationships with a minimum strength threshold
    relationships = graph_connector.query('''
                MATCH (c1:Cryptocurrency)-[r:RELATED_TO]-(c2:Cryptocurrency)
                WHERE r.common_articles > 3  // Only include strong relationships
                RETURN id(c1) AS source, id(c2) AS target, r.common_articles AS weight
            ''')
    
    nodes = []
    for row in result:
        nodes.append({
            "id": row["id"],
            "label": f"{row['name']} ({row['symbol']})",
            "title": f"{row['name']} ({row['symbol']})",
            "color": "#4C96D7"  # Light blue color
        })
    
    edges = []
    for rel in relationships:
        edges.append({
            "from": rel["source"],
            "to": rel["target"],
            "value": rel["weight"],
            "title": f"Common articles: {rel['weight']}"
        })
    
    # Create a network
    net = Network(height="600px", width="100%", notebook=False, bgcolor="#1A1A1A", font_color="white")
    
    # Add nodes and edges
    for node in nodes:
        net.add_node(node["id"], label=node["label"], title=node["title"], color=node["color"])
    
    for edge in edges:
        net.add_edge(edge["from"], edge["to"], value=edge["value"], title=edge["title"])
    
    # Set physics layout options
    net.set_options('''
    {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -100,
          "centralGravity": 0.01,
          "springLength": 200,
          "springConstant": 0.08
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
    ''')
    
    # Save visualization
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    net.save_html(output_path)
    print(f"Created cryptocurrency network visualization: {output_path}")
    
    return output_path


def create_topic_network_visualization(graph_connector, output_path="static/topic_network.html"):
    """Create topic network visualization."""
    # Query for all topics
    result = graph_connector.query('''
                MATCH (t:Topic)
                RETURN id(t) AS id, t.name AS name
            ''')
    
    # Get relationships with a minimum strength threshold
    relationships = graph_connector.query('''
                MATCH (t1:Topic)-[r:RELATED_TOPIC]-(t2:Topic)
                WHERE r.common_articles > 2  // Only include meaningful relationships
                RETURN id(t1) AS source, id(t2) AS target, r.common_articles AS weight
            ''')
    
    # Get article counts for node sizing
    article_counts = graph_connector.query('''
                MATCH (t:Topic)<-[:HAS_TOPIC]-(a:Article)
                WITH t, count(a) AS article_count
                RETURN id(t) AS id, article_count
            ''')
    
    # Build nodes
    nodes = []
    id_to_count = {row["id"]: row["article_count"] for row in article_counts}
    
    for row in result:
        # Scale node size based on article count
        size = 10 + (id_to_count.get(row["id"], 0) * 2)
        nodes.append({
            "id": row["id"],
            "label": row["name"],
            "title": f"{row['name']}: {id_to_count.get(row['id'], 0)} articles",
            "color": "#8ECAE6",  # Light blue color
            "size": size
        })
    
    # Build edges
    edges = []
    for rel in relationships:
        # Scale edge width based on strength
        width = 1 + (rel["weight"] * 0.5)
        edges.append({
            "from": rel["source"],
            "to": rel["target"],
            "value": rel["weight"],
            "title": f"Common articles: {rel['weight']}",
            "width": width
        })
    
    # Create and configure network
    net = Network(height="600px", width="100%", notebook=False, bgcolor="#1A1A1A", font_color="white")
    
    # Add nodes and edges
    for node in nodes:
        net.add_node(node["id"], label=node["label"], title=node["title"], 
                     color=node["color"], size=node["size"])
    
    for edge in edges:
        net.add_edge(edge["from"], edge["to"], value=edge["value"], 
                    title=edge["title"], width=edge["width"])
    
    # Set physics layout options
    net.set_options('''
    {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -80,
          "centralGravity": 0.01,
          "springLength": 180,
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
    ''')
    
    # Save visualization
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    net.save_html(output_path)
    print(f"Created topic network visualization: {output_path}")
    
    return output_path 