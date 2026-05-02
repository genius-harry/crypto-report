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
    """Load the scraped articles from file.

    Prefers a compilation file (`scraped_articles_*.json`) but falls back to
    merging the per-article JSON files in `data/articles/`.
    """
    articles_dir = os.path.join(os.getcwd(), "data", "articles")
    if not os.path.exists(articles_dir):
        print("No articles found")
        return []

    articles = []
    compilation_files = sorted(
        [f for f in os.listdir(articles_dir) if f.startswith('scraped_articles_') and f.endswith('.json')],
        key=lambda x: os.path.getmtime(os.path.join(articles_dir, x)),
        reverse=True,
    )

    if compilation_files:
        latest_file = os.path.join(articles_dir, compilation_files[0])
        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            articles = data.get("articles", [])
            print(f"Successfully loaded {len(articles)} articles from {latest_file}")
    else:
        # Per-article fallback
        per_article = sorted(
            [f for f in os.listdir(articles_dir) if f.endswith('.json')],
            key=lambda x: os.path.getmtime(os.path.join(articles_dir, x)),
            reverse=True,
        )
        for fname in per_article:
            try:
                with open(os.path.join(articles_dir, fname), "r", encoding="utf-8") as f:
                    article = json.load(f)
                if isinstance(article, dict) and article.get("url"):
                    articles.append(article)
            except Exception:
                continue
        print(f"Successfully loaded {len(articles)} per-article files from {articles_dir}")

    if not articles:
        print("No articles found")
        return []

    # Enhance articles with relevant counts for display
    for article in articles:
        crypto_count = sum(1 for entity in article.get("entities", [])
                          if entity.get("type") == "Cryptocurrency")
        topic_count = sum(1 for entity in article.get("entities", [])
                         if entity.get("type") == "Topic")
        article["crypto_count"] = crypto_count
        article["topic_count"] = topic_count

    return articles[:12]  # Return top 12 articles

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
    
    # Templates and static assets live in templates/ and static/ — committed
    # to the repo, edited as files. No runtime bootstrap.

    coinapi_key = os.getenv("COINAPI_KEY")
    if coinapi_key:
        print(f"CoinAPI key found: {coinapi_key[:4]}...{coinapi_key[-4:]}")
    else:
        print("No CoinAPI key found. Set the COINAPI_KEY environment variable for live data.")
        print("Using mock data for CoinAPI section.")

    # Set up GraphRAG
    graph_chain = setup_graphrag("gpt-4o")
    
    # Start Flask app
    app.run(host='127.0.0.1', debug=False, port=port)
    
if __name__ == '__main__':
    start_web_interface() 