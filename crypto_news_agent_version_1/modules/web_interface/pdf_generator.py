"""
PDF Generator Module

This module handles generating PDF reports from the web interface using ReportLab.
"""

import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.platypus.flowables import HRFlowable
from PIL import Image as PILImage
import markdown2

def markdown_to_reportlab(markdown_text, styles):
    """Convert markdown text to a list of ReportLab flowables."""
    # Convert markdown to HTML
    html = markdown2.markdown(markdown_text, extras=["tables", "fenced-code-blocks"])
    
    # Parse HTML - simple method for now, can be enhanced
    flowables = []
    
    # Split by headers and paragraphs - this is a simplified approach
    sections = html.split("<h1>")
    
    for i, section in enumerate(sections):
        if i == 0 and not section.strip():
            continue
            
        if i > 0:
            section = "<h1>" + section
            
        # Handle h1
        h1_parts = section.split("</h1>", 1)
        if len(h1_parts) > 1:
            h1_text = h1_parts[0].replace("<h1>", "").strip()
            flowables.append(Paragraph(h1_text, styles["Heading1"]))
            section = h1_parts[1]
            
        # Handle h2
        h2_sections = section.split("<h2>")
        for j, h2_section in enumerate(h2_sections):
            if j == 0 and not h2_section.strip():
                continue
                
            if j > 0:
                h2_section = "<h2>" + h2_section
                
            h2_parts = h2_section.split("</h2>", 1)
            if len(h2_parts) > 1:
                h2_text = h2_parts[0].replace("<h2>", "").strip()
                flowables.append(Paragraph(h2_text, styles["Heading2"]))
                h2_section = h2_parts[1]
                
            # Handle paragraphs
            paragraphs = h2_section.split("<p>")
            for k, para in enumerate(paragraphs):
                if k == 0 and not para.strip():
                    continue
                    
                if k > 0:
                    para = "<p>" + para
                    
                para_parts = para.split("</p>", 1)
                if len(para_parts) > 1:
                    para_text = para_parts[0].replace("<p>", "").strip()
                    # Basic HTML tag handling
                    para_text = para_text.replace("<strong>", "<b>").replace("</strong>", "</b>")
                    para_text = para_text.replace("<em>", "<i>").replace("</em>", "</i>")
                    flowables.append(Paragraph(para_text, styles["Normal"]))
                    
            flowables.append(Spacer(1, 0.2*inch))
    
    return flowables

def generate_pdf_report(report_markdown, articles, graph_image_path=None):
    """
    Generate a PDF report from the report content, graph image, and articles.
    
    Args:
        report_markdown: Markdown content of the report
        articles: List of article dictionaries
        graph_image_path: Path to the graph visualization image (optional)
        
    Returns:
        Path to the generated PDF file
    """
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.getcwd(), "output", "pdf")
    os.makedirs(output_dir, exist_ok=True)
    
    # Format timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"crypto_report_{timestamp}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)
    
    # Create the document
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Add custom styles if they don't exist
    if 'CustomTitle' not in styles:
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=12
        ))
    
    if 'CustomSubtitle' not in styles:
        styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=18,
            spaceBefore=12,
            spaceAfter=6
        ))
    
    # Create story (content)
    story = []
    
    # Add title
    title = "Cryptocurrency Market Report"
    story.append(Paragraph(title, styles["CustomTitle"]))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Italic"]))
    story.append(Spacer(1, 0.25*inch))
    
    # Add report content
    story.append(Paragraph("Market Analysis", styles["CustomSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.gray))
    story.append(Spacer(1, 0.1*inch))
    
    # Convert markdown to reportlab flowables
    report_flowables = markdown_to_reportlab(report_markdown, styles)
    story.extend(report_flowables)
    
    # Add knowledge graph visualization if available
    if graph_image_path and os.path.exists(graph_image_path):
        story.append(Spacer(1, 0.25*inch))
        story.append(Paragraph("Knowledge Graph Visualization", styles["CustomSubtitle"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.gray))
        story.append(Spacer(1, 0.1*inch))
        
        # Resize image if needed
        try:
            img = PILImage.open(graph_image_path)
            img_width, img_height = img.size
            max_width = 6 * inch  # Max width for the PDF
            if img_width > max_width:
                ratio = max_width / img_width
                new_height = img_height * ratio
                story.append(Image(graph_image_path, width=max_width, height=new_height))
            else:
                story.append(Image(graph_image_path, width=img_width, height=img_height))
        except Exception as e:
            print(f"Error adding image: {e}")
            story.append(Paragraph("Graph visualization image could not be loaded.", styles["Normal"]))
    
    # Add top articles
    if articles:
        story.append(Spacer(1, 0.25*inch))
        story.append(Paragraph("Top Crypto News Articles", styles["CustomSubtitle"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.gray))
        story.append(Spacer(1, 0.1*inch))
        
        # Create article table
        for i, article in enumerate(articles[:10]):  # Limit to top 10 articles
            title = article.get('title', 'No Title')
            snippet = article.get('snippet', 'No Snippet')
            if len(snippet) > 200:
                snippet = snippet[:200] + "..."
            
            story.append(Paragraph(f"<b>{i+1}. {title}</b>", styles["Normal"]))
            story.append(Paragraph(snippet, styles["Normal"]))
            story.append(Paragraph(f"Crypto mentions: {article.get('crypto_count', 0)} | Topic mentions: {article.get('topic_count', 0)}", styles["Italic"]))
            story.append(Spacer(1, 0.15*inch))
    
    # Add footer
    story.append(Spacer(1, 0.5*inch))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.gray))
    story.append(Paragraph("Generated by Crypto News GraphRAG System", styles["Italic"]))
    
    # Build the PDF
    doc.build(story)
    
    print(f"PDF report generated: {pdf_path}")
    return pdf_path
