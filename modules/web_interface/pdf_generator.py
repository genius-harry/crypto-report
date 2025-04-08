"""
PDF Generator Module

This module handles generating PDF reports from the web interface.
"""

import os
from datetime import datetime
from weasyprint import HTML, CSS

def generate_pdf_report(report_content_html, articles, graph_image_path=None):
    """
    Generate a PDF report from the report content, graph image, and articles.
    
    Args:
        report_content_html: HTML content of the report
        articles: List of article dictionaries
        graph_image_path: Path to the graph visualization image (optional)
        
    Returns:
        Path to the generated PDF file
    """
    # Create output directory
    output_dir = os.path.join(os.getcwd(), "output", "pdf")
    os.makedirs(output_dir, exist_ok=True)
    
    # Format timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"crypto_report_{timestamp}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)
    
    # Basic HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Cryptocurrency Market Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            h1 {{ color: #333; }}
            .article {{ margin-bottom: 15px; border: 1px solid #ddd; padding: 10px; }}
        </style>
    </head>
    <body>
        <h1>Cryptocurrency Market Report</h1>
        <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        <div>{report_content_html}</div>
        
        <h2>Top Articles</h2>
        <div>
    """
    
    # Add articles
    for i, article in enumerate(articles[:10]):
        title = article.get('title', 'No Title')
        snippet = article.get('snippet', 'No Snippet')
        html_content += f"""
        <div class="article">
            <h3>{title}</h3>
            <p>{snippet}</p>
        </div>
        """
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    # Generate PDF
    HTML(string=html_content).write_pdf(pdf_path)
    
    print(f"PDF report generated: {pdf_path}")
    return pdf_path 