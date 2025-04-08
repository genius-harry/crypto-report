from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
import os

from ..report_generator.graphrag import setup_graphrag, query_graphrag, query_graph, ask_question

# Load environment variables
# ... existing code ...

@app.route('/generate-pdf')
def generate_pdf():
    """Generate a PDF report with the current data."""
    try:
        # Get path to the original markdown report
        report_path = os.path.join(os.getcwd(), "output", "crypto_market_report.md")
        
        if os.path.exists(report_path):
            # Send the markdown file directly for now
            # In a real production environment, we would convert this to a PDF
            return send_file(report_path, as_attachment=True, download_name="crypto_market_report.md")
        else:
            return jsonify({"error": "Report file not found"}), 404
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return jsonify({"error": str(e)}), 500

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
                            <a class="btn btn-outline-light" href="/generate-pdf" target="_blank">Generate Report</a>
                        </li>
                    </ul>
                </div>
            </div>
        </nav>
    </body>
    </html>
    """

# ... existing code ... 