"""
GraphRAG Module - Fixed Version

This module handles setting up and using the GraphRAG system.
"""

import os
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from datetime import datetime
import json
import re

# Load environment variables
load_dotenv()

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Neo4j connection parameters
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def setup_graphrag(model="gpt-4o", client=None, verbose=False):
    """Set up GraphRAG chain with Neo4j"""
    if not OPENAI_API_KEY:
        print("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")
        return None
    
    try:
        # Get Neo4j credentials
        uri = os.getenv("NEO4J_URI")
        username = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        
        if not uri or not username or not password:
            error_msg = f"Missing Neo4j credentials:"
            if not uri:
                error_msg += " Did not find uri, please add an environment variable `NEO4J_URI` which contains it, or pass `uri` as a named parameter."
            if not username:
                error_msg += " Did not find username, please add an environment variable `NEO4J_USERNAME` which contains it, or pass `username` as a named parameter."
            if not password:
                error_msg += " Did not find password, please add an environment variable `NEO4J_PASSWORD` which contains it, or pass `password` as a named parameter."
            raise ValueError(error_msg)
        
        # Initialize Neo4j graph
        graph = Neo4jGraph(
            url=uri, 
            username=username, 
            password=password
        )
        
        # Initialize the LLM
        llm = ChatOpenAI(
            model=model,
            temperature=0.7,
            api_key=OPENAI_API_KEY
        )
        
        # Create the graph QA chain with proper parameters
        try:
            # First try with the allow_dangerous_requests parameter (newer versions)
            chain = GraphCypherQAChain.from_llm(
                llm=llm,
                graph=graph,
                verbose=verbose,
                allow_dangerous_requests=True
            )
        except TypeError:
            # Fallback to without the parameter (older versions)
            print("Falling back to older GraphCypherQAChain initialization")
            chain = GraphCypherQAChain.from_llm(
                llm=llm,
                graph=graph,
                verbose=verbose
            )
        
        print(f"GraphRAG system set up with {model} model")
        return chain
    
    except Exception as e:
        print(f"Error setting up GraphRAG: {e}")
        return None

def run_direct_cypher(query: str, params=None):
    """Run a Cypher query directly against Neo4j and return the results."""
    try:
        # Connect to Neo4j
        graph = Neo4jGraph(
            url=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD
        )
        
        # Execute query
        if params:
            results = graph.query(query, params=params)
        else:
            results = graph.query(query)
        return results
    except Exception as e:
        print(f"Error executing Cypher query: {e}")
        return []

def query_graphrag(chain: GraphCypherQAChain, question: str) -> str:
    """
    Query the GraphRAG system.
    
    Args:
        chain: GraphCypherQAChain object
        question: Question to ask
        
    Returns:
        Answer from the GraphRAG system
    """
    if not chain:
        return "GraphRAG system not set up."
    
    try:
        # Run the query
        result = chain.invoke({"query": question})
        
        # Extract answer
        answer = result.get("result", "No answer found.")
        return answer
    
    except Exception as e:
        print(f"Error querying GraphRAG: {e}")
        
        # Try a fallback approach with a direct question to the LLM
        try:
            llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0.9,
                api_key=OPENAI_API_KEY
            )
            
            fallback_prompt = f"""
            You are a cryptocurrency analyst tasked with answering a question. 
            The system encountered an error when trying to query the database.
            Please provide a generic, informative response to the following question 
            based on your general knowledge about cryptocurrencies:
            
            Question: {question}
            
            Provide a thoughtful, well-structured response that acknowledges the limited
            information availability but still gives useful information where possible.
            """
            
            fallback_response = llm.invoke(fallback_prompt)
            return f"⚠️ Database query failed. Using general knowledge instead:\n\n{fallback_response.content}"
        except Exception as fallback_error:
            return f"Error: Could not query the database or provide a fallback response."

def get_direct_crypto_info(crypto_name):
    """Get direct information about a specific cryptocurrency using Cypher queries."""
    try:
        # Get recent news about this cryptocurrency
        crypto_query = """
        MATCH (c:Cryptocurrency)<-[:MENTIONS_CRYPTO]-(a:Article)
        WHERE a.date IS NOT NULL AND 
              (toLower(c.name) CONTAINS toLower($crypto_name) OR toLower(c.symbol) CONTAINS toLower($crypto_name))
        WITH a, c ORDER BY a.date DESC LIMIT 5
        RETURN c.name as name, a.title as title, a.date as date, a.summary as summary
        """
        
        # Normalize crypto name
        if crypto_name.lower() in ["btc", "bitcoin"]:
            search_term = "bitcoin"
        elif crypto_name.lower() in ["eth", "ethereum"]:
            search_term = "ethereum"
        elif crypto_name.lower() in ["usdc", "usd coin"]:
            search_term = "usd coin"
        elif crypto_name.lower() in ["usdt", "tether"]:
            search_term = "tether"
        else:
            search_term = crypto_name
        
        results = run_direct_cypher(crypto_query, {"crypto_name": search_term})
        if not results or len(results) == 0:
            return None
        
        # Format a complete answer
        crypto_display_name = results[0].get('name', search_term.capitalize())
        answer = f"📈 {crypto_display_name} Updates:\n\n"
        
        for item in results:
            title = item.get('title', '')
            date = item.get('date', '')
            summary = item.get('summary', '')
            
            # Extract numbers and dates
            numbers = re.findall(r'\$[\d,]+(?:\.\d+)?|[\d,]+(?:\.\d+)?%', summary)
            
            # Format with numbers
            formatted_summary = summary[:150]
            if numbers:
                formatted_summary += f"... (Key numbers: {', '.join(numbers)})"
            else:
                formatted_summary += "..."
            
            answer += f"• {date}: {title}\n  {formatted_summary}\n\n"
        
        return answer
    except Exception as e:
        print(f"Error getting direct crypto info: {e}")
        return None

def ask_question(chain, question, chat_history=None):
    """
    Ask a question to the GraphRAG system.
    
    Args:
        chain: The GraphCypherQAChain
        question: The question to ask
        chat_history: Optional list of previous messages in the conversation
        
    Returns:
        The answer from the GraphRAG system
    """
    if not chain:
        return "GraphRAG system not set up properly. Please try again later."
    
    # Check if this is a comparison question
    comparison_keywords = ["vs", "versus", "compared to", "better than", "comparison", "difference between", "or"]
    is_comparison = any(keyword in question.lower() for keyword in comparison_keywords)
    
    # Check for specific crypto queries
    crypto_mentions = []
    all_cryptos = ["bitcoin", "ethereum", "btc", "eth", "crypto", "usdc", "usd coin", "tether", "usdt"]
    
    for crypto in all_cryptos:
        if crypto in question.lower():
            crypto_mentions.append(crypto)
    
    # Only directly query for single crypto info if it's not a comparison
    if len(crypto_mentions) == 1 and not is_comparison:
        try:
            crypto_info = get_direct_crypto_info(crypto_mentions[0])
            if crypto_info:
                return crypto_info
        except Exception as e:
            print(f"Error getting crypto info: {e}")
    
    # Enhanced query with instructions
    enhanced_query = f"""
    As a cryptocurrency analyst with access to a knowledge graph of recent crypto news:
    
    1. Focus on specific data points and numbers
    2. Include exact dates where available
    3. Keep responses concise (max 250 words)
    4. Use clear and organized formatting
    5. Do not say "I don't know" - provide useful information or state what data is missing

    User question: {question}
    """
    
    try:
        # Try to answer using GraphRAG
        response = chain.invoke({"query": enhanced_query})
        answer = response.get('result', '')
        
        # Check if we got a proper answer
        if answer and len(answer.strip()) > 15 and "I don't know" not in answer.lower():
            return answer
            
        # Fallback to generic response if the answer is inadequate
        return "Based on the latest information in our database, we don't have specific data to fully answer your question. Try asking about recent crypto news, specific cryptocurrencies like Bitcoin or Ethereum, or market trends."
            
    except Exception as e:
        print(f"Error in main GraphRAG query: {e}")
        
        # Provide a fallback using OpenAI directly
        try:
            llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0.7,
                api_key=OPENAI_API_KEY
            )
            
            fallback_prompt = f"""
            You are a cryptocurrency analyst. Please provide a helpful response to this question 
            based on general knowledge (not specific to recent news):
            
            Question: {question}
            """
            
            fallback_response = llm.invoke(fallback_prompt)
            return fallback_response.content
        except Exception as inner_e:
            print(f"Error in fallback: {inner_e}")
            return "Sorry, I couldn't retrieve the information you requested. Please try asking a different question."

def generate_direct_cypher(question: str, llm_model: str = "gpt-4o-mini") -> str:
    """
    Generate a Cypher query directly from a natural language question.
    
    Args:
        question: Natural language question
        llm_model: LLM model to use
        
    Returns:
        Cypher query
    """
    if not OPENAI_API_KEY:
        print("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")
        return ""
    
    try:
        # Initialize the LLM
        llm = ChatOpenAI(
            model=llm_model,
            temperature=0,
            api_key=OPENAI_API_KEY
        )
        
        # Create prompt
        prompt = f"""
        You are an expert Neo4j developer and need to translate a natural language question into a Cypher query.
        
        The Neo4j database has the following structure:
        
        Nodes:
        - (Article) - Properties: id, title, date, url, summary, content
        - (Cryptocurrency) - Properties: name, symbol
        - (Topic) - Properties: name
        - (Source) - Properties: name
        - (Person) - Properties: name
        
        Relationships:
        - (Article)-[:MENTIONS_CRYPTO]->(Cryptocurrency)
        - (Article)-[:HAS_TOPIC]->(Topic)
        - (Article)-[:FROM_SOURCE]->(Source)
        - (Article)-[:MENTIONS_PERSON]->(Person)
        - (Cryptocurrency)-[:RELATED_TO]-(Cryptocurrency) - Properties: common_articles
        - (Topic)-[:RELATED_TOPIC]->(Topic) - Properties: common_articles
        - (Person)-[:DISCUSSES]->(Cryptocurrency) - Properties: mentions
        
        Question: {question}
        
        Respond with ONLY the Cypher query and nothing else. Do not add markdown formatting, explanations, or any other text.
        """
        
        # Generate Cypher query
        response = llm.invoke(prompt)
        
        # Extract query
        cypher_query = response.content.strip()
        return cypher_query
    
    except Exception as e:
        print(f"Error generating Cypher query: {e}")
        return ""

def query_graph(question: str, mode: str = "graphrag") -> str:
    """
    Query the graph using either GraphRAG or direct Cypher query.
    
    Args:
        question: Question to ask
        mode: Query mode ("graphrag" or "direct_cypher")
        
    Returns:
        Answer
    """
    if mode == "graphrag":
        # Use GraphRAG
        chain = setup_graphrag()
        if chain:
            return query_graphrag(chain, question)
        else:
            return "Could not set up GraphRAG system."
    
    elif mode == "direct_cypher":
        # Use direct Cypher query
        cypher_query = generate_direct_cypher(question)
        if cypher_query:
            results = run_direct_cypher(cypher_query)
            return str(results)
        else:
            return "Could not generate Cypher query."
    
    else:
        return f"Unknown query mode: {mode}"

def save_report(report: str) -> None:
    """Save the report to a file."""
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    report_path = os.path.join(output_dir, "crypto_market_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to {report_path}")

def generate_report(chain, model="gpt-4o"):
    """Generate a comprehensive crypto market report using actual GraphRAG data with detailed analysis."""
    print("Generating comprehensive crypto market report with GraphRAG...")
    
    # Initialize LLM with higher context capacity
    try:
        llm = ChatOpenAI(
            model=model,
            temperature=0.8,
            api_key=OPENAI_API_KEY
        )
        
        # Lower context LLM for preprocessing
        summarizing_llm = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0.5,
            api_key=OPENAI_API_KEY
        )
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        return "Error initializing LLM. Please check your OpenAI API key."
    
    # 1. Get recent significant events
    print("Fetching recent significant events...")
    recent_events_query = """
    MATCH (a:Article)-[:MENTIONS_CRYPTO]->(c:Cryptocurrency)
    WHERE a.date IS NOT NULL
    WITH a, collect(c.name) as cryptos
    RETURN a.title as title, a.url as url, a.date as date, a.summary as summary, cryptos
    ORDER BY a.date DESC
    LIMIT 5
    """
    
    try:
        recent_events = run_direct_cypher(recent_events_query)
        print(f"Found {len(recent_events)} recent events")
    except Exception as e:
        print(f"Error fetching recent events: {e}")
        recent_events = []
    
    # Format events with comprehensive analysis
    events_content = ""
    if recent_events:
        # First, pre-process each event to create condensed summaries
        events_data = []
        for i, event in enumerate(recent_events):
            print(f"Processing event {i+1}/{len(recent_events)}: {event.get('title', 'Untitled')}")
            title = event.get('title', 'Untitled')
            date_str = event.get('date', 'Recent')
            if isinstance(date_str, str) and len(date_str) > 10:
                date_str = date_str[:10]
            url = event.get('url', '#')
            summary = event.get('summary', '')
            mentioned_cryptos = event.get('cryptos', [])
            
            # Pre-summarize if needed
            if len(summary) > 200:
                try:
                    mini_summary = summarizing_llm.invoke(
                        f"Summarize this in 2-3 sentences: {summary[:1000]}..."
                    ).content
                except Exception as e:
                    print(f"Error creating mini-summary: {e}")
                    mini_summary = summary[:200] + "..."
            else:
                mini_summary = summary
                
            events_data.append({
                "title": title,
                "date": date_str,
                "url": url,
                "summary": mini_summary,
                "cryptos": mentioned_cryptos
            })
        
        # Generate a comprehensive analysis of all events
        events_analysis_prompt = f"""
        Based on these recent cryptocurrency news events, provide a comprehensive analysis of what's happening in the market:
        
        {json.dumps(events_data, indent=2)}
        
        For each event:
        1. Provide a detailed explanation of what happened and why it matters
        2. Discuss potential market implications for investors
        3. Include specific details from the articles
        
        Write in a detailed analytical style with substantive paragraphs, NOT just summaries or bullet points.
        Structure the content with clear headings for each major event.
        Include links to the original sources with proper formatting.
        """
        
        try:
            print("Generating events analysis...")
            events_analysis = llm.invoke(events_analysis_prompt).content.strip()
            events_content = events_analysis
        except Exception as e:
            print(f"Error generating events analysis: {e}")
            # Fallback to basic formatting if analysis fails
            for event in events_data:
                events_content += f"### {event['title']}\n"
                events_content += f"**Date:** {event['date']} | **Cryptocurrencies mentioned:** {', '.join(event['cryptos'])}\n\n"
                events_content += f"{event['summary']}\n\n"
                events_content += f"[Read more]({event['url']})\n\n"
    else:
        events_content = "No recent events found in the database. The GraphRAG system was unable to retrieve current events.\n\n"
    
    # 2. Get market trends for major cryptocurrencies
    print("Analyzing cryptocurrency market trends...")
    market_trends_query = """
    MATCH (c:Cryptocurrency)<-[r:MENTIONS_CRYPTO]-(a:Article)
    WITH c, count(r) as mentions
    ORDER BY mentions DESC
    LIMIT 5
    OPTIONAL MATCH (c)<-[:MENTIONS_CRYPTO]-(article:Article)
    WHERE article.date IS NOT NULL
    WITH c, mentions, collect({title: article.title, date: article.date, url: article.url}) as articles
    ORDER BY mentions DESC
    RETURN c.name as name, c.symbol as symbol, mentions, articles[..5] as recent_articles
    """
    
    try:
        crypto_trends = run_direct_cypher(market_trends_query)
        print(f"Analyzing trends for {len(crypto_trends)} cryptocurrencies")
    except Exception as e:
        print(f"Error fetching cryptocurrency trends: {e}")
        crypto_trends = []
    
    trends_content = ""
    if crypto_trends:
        # Process each cryptocurrency separately to avoid token limits
        all_crypto_analyses = []
        
        for crypto in crypto_trends:
            name = crypto.get('name', 'Unknown')
            symbol = crypto.get('symbol', '')
            mentions = crypto.get('mentions', 0)
            articles = crypto.get('recent_articles', [])
            
            crypto_prompt = f"""
            Provide a detailed analysis of {name} ({symbol}) based on these recent articles:
            
            {json.dumps(articles, indent=2)}
            
            Your analysis should:
            1. Discuss key price movements or market activities
            2. Identify major factors driving its current position
            3. Note how this cryptocurrency compares to others in the market
            
            Write a comprehensive paragraph (not bullet points) that provides true analytical depth.
            """
            
            try:
                print(f"Analyzing {name}...")
                crypto_analysis = summarizing_llm.invoke(crypto_prompt).content.strip()
                all_crypto_analyses.append(f"### {name} ({symbol})\n\n{crypto_analysis}\n\n")
            except Exception as e:
                print(f"Error analyzing {name}: {e}")
                all_crypto_analyses.append(f"### {name} ({symbol})\n\nAnalysis unavailable due to an error.\n\n")
        
        # Combine all crypto analyses
        trends_content = "".join(all_crypto_analyses)
        
        # Add a market overview section
        market_overview_prompt = f"""
        Based on the data about these top cryptocurrencies, provide a comprehensive market overview paragraph:
        
        {json.dumps([{
            "name": crypto.get('name', 'Unknown'),
            "symbol": crypto.get('symbol', ''),
            "mentions": crypto.get('mentions', 0)
        } for crypto in crypto_trends], indent=2)}
        
        Write a detailed paragraph analyzing the overall market trends and relationships between these cryptocurrencies.
        """
        
        try:
            print("Creating market overview...")
            market_overview = llm.invoke(market_overview_prompt).content.strip()
            trends_content = f"## Market Overview\n\n{market_overview}\n\n## Individual Cryptocurrency Analysis\n\n" + trends_content
        except Exception as e:
            print(f"Error generating market overview: {e}")
    else:
        trends_content = "No cryptocurrency market trend data available in the database.\n\n"
    
    # 3. Get regulatory information
    print("Analyzing regulatory landscape...")
    regulatory_query = """
    MATCH (a:Article)-[:HAS_TOPIC]->(t:Topic)
    WHERE t.name IN ['Regulation', 'Regulatory', 'SEC', 'CFTC', 'Law', 'Compliance', 'Legal']
    AND a.date IS NOT NULL
    WITH a
    ORDER BY a.date DESC
    LIMIT 5
    RETURN a.title as title, a.url as url, a.date as date, a.summary as summary
    """
    
    try:
        regulatory_news = run_direct_cypher(regulatory_query)
        print(f"Found {len(regulatory_news)} regulatory articles")
    except Exception as e:
        print(f"Error fetching regulatory news: {e}")
        regulatory_news = []
    
    regulatory_content = ""
    if regulatory_news:
        # Preprocess to ensure we don't hit token limits
        reg_data = []
        for reg in regulatory_news:
            title = reg.get('title', 'Untitled')
            date_str = reg.get('date', 'Recent')
            if isinstance(date_str, str) and len(date_str) > 10:
                date_str = date_str[:10]
            url = reg.get('url', '#')
            summary = reg.get('summary', '')
            
            # Pre-summarize if needed
            if len(summary) > 200:
                try:
                    mini_summary = summarizing_llm.invoke(
                        f"Summarize this regulatory news in 2-3 sentences: {summary[:1000]}..."
                    ).content
                except Exception as e:
                    print(f"Error creating regulatory mini-summary: {e}")
                    mini_summary = summary[:200] + "..."
            else:
                mini_summary = summary
                
            reg_data.append({
                "title": title,
                "date": date_str,
                "url": url,
                "summary": mini_summary
            })
        
        regulatory_analysis_prompt = f"""
        Based on these recent articles about cryptocurrency regulation, provide a comprehensive analysis of the current regulatory landscape:
        
        {json.dumps(reg_data, indent=2)}
        
        Your analysis should:
        1. Identify the major regulatory developments and their broader implications
        2. Analyze how different jurisdictions are approaching cryptocurrency regulation
        3. Discuss potential impacts on different cryptocurrencies and the market as a whole
        
        Write in a detailed analytical style with substantive paragraphs that incorporate specific information from the articles.
        Include links to the original sources with proper formatting.
        """
        
        try:
            print("Analyzing regulatory landscape...")
            regulatory_analysis = llm.invoke(regulatory_analysis_prompt).content.strip()
            regulatory_content = regulatory_analysis
        except Exception as e:
            print(f"Error generating regulatory analysis: {e}")
            # Fallback
            for reg in reg_data:
                regulatory_content += f"### {reg['title']}\n"
                regulatory_content += f"**Date:** {reg['date']}\n\n"
                regulatory_content += f"{reg['summary']}\n\n"
                regulatory_content += f"[Read more]({reg['url']})\n\n"
    else:
        regulatory_content = "No recent regulatory developments found in the database.\n\n"
    
    # 4. Generate executive summary based on all collected data
    print("Creating executive summary...")
    summary_prompt = f"""
    Create a comprehensive executive summary of the current cryptocurrency market based on this data:
    
    MARKET OVERVIEW:
    {trends_content[:800]}...
    
    RECENT EVENTS:
    {events_content[:800]}...
    
    REGULATORY DEVELOPMENTS:
    {regulatory_content[:800]}...
    
    Your executive summary should:
    1. Provide a holistic view of the current state of the cryptocurrency market
    2. Highlight the most significant recent developments across all areas
    3. Discuss interconnections between events, trends, and regulations
    
    Write 3-4 detailed paragraphs (not bullet points) that give investors a complete understanding of the current landscape.
    """
    
    try:
        executive_summary = llm.invoke(summary_prompt).content.strip()
    except Exception as e:
        print(f"Error generating executive summary: {e}")
        executive_summary = "Executive summary could not be generated due to an error.\n\n"
    
    # 5. Generate investment implications
    print("Analyzing investment implications...")
    implications_prompt = f"""
    Based on the cryptocurrency market data below, provide a comprehensive analysis of investment implications:
    
    MARKET OVERVIEW:
    {trends_content[:800]}...
    
    RECENT EVENTS:
    {events_content[:800]}...
    
    REGULATORY DEVELOPMENTS:
    {regulatory_content[:800]}...
    
    Your analysis should:
    1. Discuss specific investment opportunities and risks based on the data
    2. Provide nuanced guidance for different investor profiles (conservative, moderate, aggressive)
    3. Analyze potential short-term and long-term market movements
    
    Write substantive paragraphs with specific, actionable insights based directly on the news data.
    Provide analytical depth rather than generic investment advice.
    """
    
    try:
        investment_implications = llm.invoke(implications_prompt).content.strip()
    except Exception as e:
        print(f"Error generating investment implications: {e}")
        investment_implications = "Investment implications could not be generated due to an error.\n\n"
    
    # Format the complete report
    report = f"""# Cryptocurrency Market Report for Investors
Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary
<tag>SUMMARY</tag>
{executive_summary}

## Recent Significant Events
<tag>EVENTS</tag>
{events_content}

## Market Trends Analysis
<tag>TRENDS</tag>
{trends_content}

## Regulatory Landscape
<tag>REGULATORY</tag>
{regulatory_content}

## Investment Implications
<tag>INVESTMENT</tag>
{investment_implications}

---
*Note: This report is generated using GraphRAG analysis of recent crypto news and market data. Always conduct your own research before making investment decisions.*
"""
    
    # Save the report
    save_report(report)
    
    return report 