"""
Web Interface Module

This module handles the Flask web interface for the crypto news GraphRAG system.
"""

import os
import json
import webbrowser
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import markdown2
from markupsafe import Markup
import re
import requests  # Added import for making HTTP requests
import logging  # Add logging for better error tracking

from flask import Flask, render_template, request, jsonify, send_file, session
from dotenv import load_dotenv

from ..report_generator.graphrag import setup_graphrag, query_graphrag, query_graph, ask_question, get_market_sentiment

# Load environment variables
load_dotenv()

# Directory paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(CURRENT_DIR)), 'static')
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(CURRENT_DIR)), 'templates')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(CURRENT_DIR)), 'output')

# Ensure directories exist
for dir_path in [STATIC_DIR, TEMPLATES_DIR, OUTPUT_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Initialize Flask app
app = Flask(
    __name__,
    template_folder=os.path.abspath(TEMPLATES_DIR),
    static_folder=os.path.abspath(STATIC_DIR)
)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "crypto-graphrag-secret-key")

# Global variables
graph_chain = None
report_content = ""
report_content_html = ""
article_rankings = []
chat_histories = {}  # Store chat histories by session ID

def create_html_templates():
    """Create HTML templates for the web interface."""
    # Create main index.html template
    index_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Crypto News GraphRAG System</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
        <script src="https://d3js.org/d3.v7.min.js"></script>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
            <div class="container">
                <a class="navbar-brand" href="#">Crypto News GraphRAG</a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNav">
                    <ul class="navbar-nav">
                        <li class="nav-item">
                            <a class="nav-link" href="#market-sentiment">Market Sentiment</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="#coinapi-section">CoinAPI Data</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="#report">Market Report</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="#chat">Chat</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="#visualization">Visualization</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="#articles">Top Articles</a>
                        </li>
                    </ul>
                    <ul class="navbar-nav ms-auto">
                        <li class="nav-item">
                            <a class="btn btn-outline-light" href="/generate-pdf" target="_blank">Generate PDF Report</a>
                        </li>
                    </ul>
                </div>
            </div>
        </nav>

        <div class="container mt-4">
            <!-- Market Sentiment Section -->
            <section id="market-sentiment" class="mb-5">
                <h2 class="mb-4">Current Market Sentiment</h2>
                <div class="row">
                    <div class="col-md-6">
                        <div class="card border-success mb-3">
                            <div class="card-header bg-success text-white">
                                <h4 class="mb-0">🚀 Bullish Outlook</h4>
                            </div>
                            <div class="card-body">
                                <p class="card-text">{{ bullish_summary }}</p>
                                <div class="table-responsive">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>Cryptocurrency</th>
                                                <th>Mentions</th>
                                                <th>Recent News</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {% for crypto in bullish_cryptos %}
                                            <tr>
                                                <td>{{ crypto.name }} {% if crypto.symbol %}({{ crypto.symbol }}){% endif %}</td>
                                                <td>{{ crypto.count }}</td>
                                                <td>
                                                    <ul class="small mb-0">
                                                        {% for reason in crypto.reasons %}
                                                        <li>{{ reason }}</li>
                                                        {% endfor %}
                                                    </ul>
                                                </td>
                                            </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card border-danger mb-3">
                            <div class="card-header bg-danger text-white">
                                <h4 class="mb-0">📉 Bearish Outlook</h4>
                            </div>
                            <div class="card-body">
                                <p class="card-text">{{ bearish_summary }}</p>
                                <div class="table-responsive">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>Cryptocurrency</th>
                                                <th>Mentions</th>
                                                <th>Recent News</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {% for crypto in bearish_cryptos %}
                                            <tr>
                                                <td>{{ crypto.name }} {% if crypto.symbol %}({{ crypto.symbol }}){% endif %}</td>
                                                <td>{{ crypto.count }}</td>
                                                <td>
                                                    <ul class="small mb-0">
                                                        {% for reason in crypto.reasons %}
                                                        <li>{{ reason }}</li>
                                                        {% endfor %}
                                                    </ul>
                                                </td>
                                            </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- CoinAPI Data Section -->
            <section id="coinapi-section" class="mb-5">
                <h2 class="mb-4">CoinAPI Indexes</h2>
                <div class="card">
                    <div class="card-body">
                        {% if coinapi_data and coinapi_data|length > 0 %}
                            <div class="table-responsive">
                                <table class="table table-striped">
                                    <thead class="table-dark">
                                        <tr>
                                            <th>Index ID</th>
                                            <th>Name</th>
                                            <th>Description</th>
                                            <th>Last Value</th>
                                            <th>Asset Pairs</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for index in coinapi_data %}
                                        <tr>
                                            <td><strong>{{ index.index_id }}</strong></td>
                                            <td>{{ index.name }}</td>
                                            <td>{{ index.description }}</td>
                                            <td>
                                                {% if index.last_value is defined %}
                                                    {{ index.last_value }}
                                                {% else %}
                                                    N/A
                                                {% endif %}
                                            </td>
                                            <td>
                                                {% if index.asset_pairs is defined and index.asset_pairs|length > 0 %}
                                                    <ul class="list-unstyled mb-0">
                                                    {% for pair in index.asset_pairs[:3] %}
                                                        <li>{{ pair }}</li>
                                                    {% endfor %}
                                                    {% if index.asset_pairs|length > 3 %}
                                                        <li>+ {{ index.asset_pairs|length - 3 }} more</li>
                                                    {% endif %}
                                                    </ul>
                                                {% else %}
                                                    N/A
                                                {% endif %}
                                            </td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                            <p class="text-muted small text-end">Data source: <a href="https://www.coinapi.io/" target="_blank">CoinAPI.io</a></p>
                        {% else %}
                            <div class="alert alert-info">
                                No CoinAPI index data available. This could be due to API limits, missing API key, or a temporary service issue.
                            </div>
                        {% endif %}
                    </div>
                </div>
            </section>

            <!-- Market Report Section -->
            <section id="report" class="mb-5">
                <h2 class="mb-4">Cryptocurrency Market Report</h2>
                <div class="card">
                    <div class="card-body" id="report-content">
                        {{ report_content|safe }}
                    </div>
                </div>
            </section>

            <!-- Chat Section -->
            <section id="chat" class="mb-5">
                <h2 class="mb-4">Chat with Crypto GraphRAG</h2>
                <div class="card">
                    <div class="card-body">
                        <div id="chat-messages" class="mb-3">
                            <div class="system-message">
                                Welcome to the Crypto News GraphRAG assistant. Ask me anything about the latest cryptocurrency news and trends!
                            </div>
                        </div>
                        <div class="input-group">
                            <input type="text" id="chat-input" class="form-control" placeholder="Ask a question about crypto news...">
                            <button class="btn btn-primary" id="send-button">Send</button>
                            <button class="btn btn-danger ms-2" id="reset-chat">Reset Chat</button>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Visualization Section -->
            <section id="visualization" class="mb-5">
                <h2 class="mb-4">Knowledge Graph Visualization</h2>
                <div class="row">
                    <div class="col-md-12">
                        <div class="card mb-4">
                            <div class="card-header">
                                <ul class="nav nav-tabs card-header-tabs" id="viz-tabs">
                                    <li class="nav-item">
                                        <a class="nav-link active" data-bs-toggle="tab" href="#interactive-graph">Interactive Graph</a>
                                    </li>
                                    <li class="nav-item">
                                        <a class="nav-link" data-bs-toggle="tab" href="#crypto-network">Cryptocurrency Network</a>
                                    </li>
                                    <li class="nav-item">
                                        <a class="nav-link" data-bs-toggle="tab" href="#topic-network">Topic Network</a>
                                    </li>
                                </ul>
                            </div>
                            <div class="card-body">
                                <div class="tab-content">
                                    <div class="tab-pane fade show active" id="interactive-graph">
                                        <div id="graph-container" style="height: 600px; border: 1px solid #ddd; border-radius: 5px;"></div>
                                    </div>
                                    <div class="tab-pane fade" id="crypto-network">
                                        <iframe src="{{ url_for('static', filename='crypto_network.html') }}" 
                                                width="100%" height="600px" frameborder="0"></iframe>
                                    </div>
                                    <div class="tab-pane fade" id="topic-network">
                                        <iframe src="{{ url_for('static', filename='topic_network.html') }}" 
                                                width="100%" height="600px" frameborder="0"></iframe>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Top Articles Section -->
            <section id="articles" class="mb-5">
                <h2 class="mb-4">Top Crypto News Articles</h2>
                <div class="row">
                    {% for article in articles %}
                    <div class="col-md-6 mb-4">
                        <div class="card h-100">
                            <div class="card-header d-flex justify-content-between align-items-center">
                                <span class="rank-badge">#{{ loop.index }}</span>
                                <div class="score-info">
                                    <span class="badge bg-primary">Crypto: {{ article.crypto_count }}</span>
                                    <span class="badge bg-secondary">Topics: {{ article.topic_count }}</span>
                                </div>
                            </div>
                            <div class="card-body">
                                <h5 class="card-title">{{ article.title }}</h5>
                                <p class="card-text snippet">{{ article.snippet }}</p>
                            </div>
                            <div class="card-footer">
                                <a href="{{ article.url }}" target="_blank" class="btn btn-sm btn-outline-primary">Read Full Article</a>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </section>
        </div>

        <footer class="bg-dark text-white py-4">
            <div class="container text-center">
                <p>Crypto News GraphRAG System | Generated on {{ generation_date }}</p>
            </div>
        </footer>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        <script src="{{ url_for('static', filename='app.js') }}"></script>
    </body>
    </html>
    """
    
    with open(os.path.join(TEMPLATES_DIR, 'index.html'), 'w') as f:
        f.write(index_html)
    
    print("HTML template created")
    
    # Don't overwrite CSS file if it exists
    if not os.path.exists(os.path.join(STATIC_DIR, 'styles.css')):
        css = """
        body {
            background-color: #f8f9fa;
        }
        
        .navbar-brand {
            font-weight: bold;
        }
        
        #report-content {
            white-space: pre-line;
        }
        
        #chat-messages {
            height: 400px;
            overflow-y: auto;
            padding: 10px;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .user-message {
            background-color: #e9ecef;
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 5px;
            max-width: 80%;
            margin-left: auto;
            word-wrap: break-word;
        }
        
        .assistant-message {
            background-color: #d1e7ff;
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 5px;
            max-width: 80%;
            word-wrap: break-word;
        }
        
        .system-message {
            color: #6c757d;
            font-style: italic;
            padding: 5px;
            margin-bottom: 5px;
            text-align: center;
        }
        
        #graph-container {
            background-color: #222;
        }
        
        .rank-badge {
            background-color: #6c757d;
            color: white;
            padding: 5px 10px;
            border-radius: 50%;
            font-weight: bold;
        }
        
        .snippet {
            color: #6c757d;
            font-size: 0.9rem;
        }
        
        .score-info {
            display: flex;
            gap: 5px;
        }
        
        .node {
            stroke: #fff;
            stroke-width: 1.5px;
        }
        
        .link {
            stroke: #999;
            stroke-opacity: 0.6;
        }
        
        .node text {
            font-size: 10px;
            fill: white;
        }
        """
        
        with open(os.path.join(STATIC_DIR, 'styles.css'), 'w') as f:
            f.write(css)
        print("CSS file created")
    else:
        print("CSS file already exists, not overwriting")

def load_report():
    """Load the investor report from file."""
    report_path = os.path.join(os.getcwd(), "output", "crypto_market_report.md")
    
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"Successfully loaded report from {report_path}")
            return content
    else:
        print(f"Report not found at {report_path}")
        return "# Cryptocurrency Market Report\n\nNo report available yet. Please generate a report first."

def load_articles():
    """Load the scraped articles from file."""
    articles_dir = os.path.join(os.getcwd(), "data", "articles")
    
    if os.path.exists(articles_dir):
        files = sorted([f for f in os.listdir(articles_dir) if f.startswith('scraped_articles_')], 
                       key=lambda x: os.path.getmtime(os.path.join(articles_dir, x)), 
                       reverse=True)
        
        if files:
            latest_file = os.path.join(articles_dir, files[0])
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                articles = data.get("articles", [])
                print(f"Successfully loaded {len(articles)} articles from {latest_file}")
                
                # Enhance articles with relevant counts for display
                for article in articles:
                    # Count mentions of cryptocurrencies and topics (simplified approach)
                    crypto_count = sum(1 for entity in article.get("entities", []) 
                                      if entity.get("type") == "Cryptocurrency")
                    topic_count = sum(1 for entity in article.get("entities", []) 
                                     if entity.get("type") == "Topic")
                    
                    article["crypto_count"] = crypto_count
                    article["topic_count"] = topic_count
                
                return articles[:12]  # Return top 12 articles
    
    print("No articles found")
    return []

def process_markdown(markdown_text):
    """
    Process markdown text with special handling for custom tags.
    """
    # Convert markdown to HTML
    html = markdown2.markdown(markdown_text, extras=["tables", "fenced-code-blocks"])
    
    # Process custom tags
    html = re.sub(r'<tag>(\w+)</tag>', r'<span class="tag tag-\1">\1</span>', html)
    
    # Add Bootstrap classes to tables
    html = html.replace('<table>', '<table class="table table-bordered table-striped">')
    
    return Markup(html)  # Mark as safe HTML

@app.route('/')
def index():
    """Render the main page with the investor report."""
    # Get market sentiment data
    sentiment_data = get_market_sentiment()
    bullish_cryptos = sentiment_data['bullish']['cryptos']
    bearish_cryptos = sentiment_data['bearish']['cryptos']
    bullish_summary = sentiment_data['bullish']['summary']
    bearish_summary = sentiment_data['bearish']['summary']
    
    # Get CoinAPI indexes data
    coinapi_data = []
    try:
        coinapi_key = os.getenv("COINAPI_KEY")
        
        # Log whether we have the API key
        if coinapi_key:
            logging.info("CoinAPI key found in environment variables")
            url = "https://rest.coinapi.io/v1/indexes"
            headers = {"X-CoinAPI-Key": coinapi_key}
            
            # Add timeout to prevent hanging
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                all_indexes = response.json()
                
                # Process the data to ensure it has all required fields
                processed_indexes = []
                for index in all_indexes:
                    # Ensure all required fields exist, with defaults if missing
                    processed_index = {
                        "index_id": index.get("index_id", "Unknown"),
                        "name": index.get("name", "Unnamed Index"),
                        "description": index.get("description", "No description available"),
                        "last_value": index.get("last_value", "N/A"),
                        "asset_pairs": index.get("asset_pairs", [])
                    }
                    processed_indexes.append(processed_index)
                
                # Sort by index ID for consistency
                processed_indexes.sort(key=lambda x: x["index_id"])
                
                # Limit to top 5 indexes for display
                coinapi_data = processed_indexes[:5] if len(processed_indexes) > 5 else processed_indexes
                logging.info(f"Successfully fetched and processed {len(coinapi_data)} CoinAPI indexes")
            elif response.status_code == 401:
                logging.error("CoinAPI authentication failed - invalid API key")
            elif response.status_code == 429:
                logging.error("CoinAPI rate limit exceeded")
            else:
                logging.error(f"Error fetching CoinAPI data: Status code {response.status_code}")
        else:
            logging.warning("No CoinAPI key found in environment variables, using mock data")
    except requests.exceptions.Timeout:
        logging.error("Timeout while fetching CoinAPI data")
    except requests.exceptions.ConnectionError:
        logging.error("Connection error while fetching CoinAPI data")
    except Exception as e:
        logging.error(f"Error fetching CoinAPI data: {str(e)}")
    
    # Use mock data if no data was fetched or in case of errors
    if not coinapi_data:
        logging.info("Using mock CoinAPI data")
        coinapi_data = [
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
    
    # Get report content
    report_content = load_report()
    html_content = process_markdown(report_content)
    
    # Get articles
    articles = load_articles()
    generation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return render_template(
        'index.html', 
        report_content=html_content, 
        articles=articles, 
        generation_date=generation_date,
        bullish_cryptos=bullish_cryptos,
        bearish_cryptos=bearish_cryptos,
        bullish_summary=bullish_summary,
        bearish_summary=bearish_summary,
        coinapi_data=coinapi_data
    )

@app.route('/generate-pdf')
def generate_pdf():
    """Generate a PDF report with the current data."""
    try:
        # Get the markdown report content
        report_path = os.path.join(os.getcwd(), "output", "crypto_market_report.md")
        
        if not os.path.exists(report_path):
            return jsonify({"error": "Report file not found"}), 404
            
        # Read the markdown report
        with open(report_path, "r", encoding="utf-8") as f:
            report_markdown = f.read()
        
        # Load articles
        articles = load_articles()
        
        # Get market sentiment data
        sentiment_data = get_market_sentiment()
        
        # Get CoinAPI indexes data
        coinapi_data = []
        try:
            coinapi_key = os.getenv("COINAPI_KEY")
            
            if coinapi_key:
                url = "https://rest.coinapi.io/v1/indexes"
                headers = {"X-CoinAPI-Key": coinapi_key}
                
                response = requests.get(url, headers=headers, timeout=5)
                
                if response.status_code == 200:
                    all_indexes = response.json()
                    processed_indexes = []
                    for index in all_indexes:
                        processed_index = {
                            "index_id": index.get("index_id", "Unknown"),
                            "name": index.get("name", "Unnamed Index"),
                            "description": index.get("description", "No description available"),
                            "last_value": index.get("last_value", "N/A"),
                            "asset_pairs": index.get("asset_pairs", [])
                        }
                        processed_indexes.append(processed_index)
                    
                    processed_indexes.sort(key=lambda x: x["index_id"])
                    coinapi_data = processed_indexes[:5] if len(processed_indexes) > 5 else processed_indexes
        except Exception as e:
            logging.error(f"Error fetching CoinAPI data for PDF: {e}")
        
        # Use mock data if no data was fetched
        if not coinapi_data:
            coinapi_data = [
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
                    "index_id": "DEFI",
                    "name": "CoinDesk DeFi Index",
                    "description": "Tracks the performance of decentralized financial assets across the market.",
                    "last_value": 845.29,
                    "asset_pairs": ["UNI/USD", "AAVE/USD", "COMP/USD", "SNX/USD", "MKR/USD"]
                }
            ]
        
        # Path to the graph visualization image
        graph_image_path = os.path.join(STATIC_DIR, 'crypto_network.png')
        if not os.path.exists(graph_image_path):
            graph_image_path = None
        
        # Import the PDF generator
        from .pdf_generator import generate_pdf_report
        
        # Generate the PDF file with all data
        pdf_path = generate_pdf_report(
            report_markdown, 
            articles, 
            graph_image_path,
            sentiment_data,
            coinapi_data
        )
        
        # Send the PDF file to the client
        return send_file(pdf_path, as_attachment=True, download_name=os.path.basename(pdf_path))
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/graph-data')
def graph_data():
    """Return graph data for D3.js visualization."""
    try:
        # Load graph data from file
        data_path = os.path.join(STATIC_DIR, 'graph_data.json')
        if os.path.exists(data_path):
            with open(data_path, 'r') as f:
                data = json.load(f)
            return jsonify(data)
        else:
            print(f"Graph data file not found: {data_path}")
            return jsonify({"nodes": [], "links": []})
    except Exception as e:
        print(f"Error loading graph data: {e}")
        return jsonify({"nodes": [], "links": []})

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat queries and return responses from the GraphRAG system."""
    global graph_chain, chat_histories
    
    # Setup GraphRAG if not already set up
    if graph_chain is None:
        graph_chain = setup_graphrag(model="gpt-4o")
    
    data = request.json
    message = data.get('message', '')
    
    if not message:
        return jsonify({"response": "I didn't receive a question. Please try again."})
    
    if not graph_chain:
        return jsonify({"response": "The GraphRAG system is not initialized yet. Please try again later."})
    
    # Get or create session ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_id = session['session_id']
    
    # Initialize chat history for this session if it doesn't exist
    if session_id not in chat_histories:
        chat_histories[session_id] = []
    
    # Add user message to chat history
    chat_histories[session_id].append({"role": "user", "content": message})
    
    try:
        # Query the GraphRAG system with context from chat history
        response = ask_question(graph_chain, message, chat_history=chat_histories[session_id])
        
        # Add assistant response to chat history
        chat_histories[session_id].append({"role": "assistant", "content": response})
        
        # Prevent chat history from growing too large (keep last 10 messages)
        if len(chat_histories[session_id]) > 20:
            chat_histories[session_id] = chat_histories[session_id][-20:]
        
        return jsonify({"response": response})
    except Exception as e:
        print(f"Error querying GraphRAG: {e}")
        return jsonify({"response": "I encountered an error processing your question. Please try a different question."})

@app.route('/reset-chat', methods=['POST'])
def reset_chat():
    """Reset the chat history for the current session."""
    global chat_histories
    
    # Get session ID
    if 'session_id' in session:
        session_id = session['session_id']
        
        # Clear chat history for this session
        if session_id in chat_histories:
            chat_histories[session_id] = []
            print(f"Chat history reset for session {session_id}")
        
        # Create a new session ID to fully reset
        session['session_id'] = str(uuid.uuid4())
        new_session_id = session['session_id']
        chat_histories[new_session_id] = []
        print(f"Created new session {new_session_id}")
    
    return jsonify({
        "status": "success", 
        "message": "Chat history has been reset successfully. You can start a new conversation.",
        "new_session": True
    })

@app.route('/ask', methods=['POST'])
def ask():
    """Handle questions from the user."""
    global graph_chain
    
    data = request.get_json()
    question = data.get('question', '')
    
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    # Set up GraphRAG if not already done
    if not graph_chain:
        graph_chain = setup_graphrag("gpt-4o")
        if not graph_chain:
            return jsonify({"error": "Could not set up GraphRAG"}), 500
    
    # Get answer
    try:
        answer = ask_question(graph_chain, question)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def start_web_interface(port=5000):
    """Start the web interface."""
    global graph_chain
    
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Force regenerate HTML templates, but don't overwrite existing JS/CSS files
    create_html_templates()
    print("Templates initialized")
    
    # Check if CoinAPI key is available
    coinapi_key = os.getenv("COINAPI_KEY")
    if coinapi_key:
        print(f"CoinAPI key found: {coinapi_key[:4]}...{coinapi_key[-4:]}")
    else:
        print("No CoinAPI key found. Set the COINAPI_KEY environment variable for live data.")
        print("Using mock data for CoinAPI section.")
    
    # Create default JavaScript file if it doesn't exist
    js_file_path = os.path.join(STATIC_DIR, 'app.js')
    if not os.path.exists(js_file_path):
        print("Creating default app.js file")
        with open(js_file_path, 'w') as f:
            f.write('// Default app.js file created\n')
            f.write('document.addEventListener("DOMContentLoaded", function() {\n')
            f.write('    console.log("Web interface loaded");\n')
            f.write('});\n')
    else:
        print("JavaScript file already exists, not overwriting")
    
    # Set up GraphRAG
    graph_chain = setup_graphrag("gpt-4o")
    
    # Start Flask app
    app.run(host='127.0.0.1', debug=False, port=port)
    
if __name__ == '__main__':
    start_web_interface() 