"""
Crypto News Ranker Module

This module handles ranking crypto news articles based on relevance and other criteria.
"""

import os
import json
import re
from typing import Dict, List, Any
from datetime import datetime
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Try to import the Google GenerativeAI library
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("Google GenerativeAI library not available. Install with: pip install google-generativeai")

def rank_with_keywords(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank articles based on keyword relevance.
    
    Args:
        articles: List of articles to rank
        
    Returns:
        List of articles sorted by relevance score
    """
    # Define keywords and their weights
    keywords = {
        "bitcoin": 10,
        "btc": 10,
        "ethereum": 9,
        "eth": 9,
        "crypto": 8,
        "blockchain": 8,
        "cryptocurrency": 8,
        "defi": 7,
        "nft": 6,
        "token": 6,
        "altcoin": 6,
        "mining": 5,
        "wallet": 5,
        "exchange": 5,
        "market": 5,
        "price": 5,
        "investment": 4,
        "regulation": 4,
        "adoption": 4,
        "trading": 4,
        "analysis": 3,
        "tech": 3,
        "technology": 3,
        "finance": 3,
        "payment": 3
    }
    
    # Calculate score for each article
    for article in articles:
        score = 0
        title = article.get("title", "").lower()
        snippet = article.get("snippet", "").lower()
        
        # Check title
        for keyword, weight in keywords.items():
            if keyword in title:
                score += weight * 2  # Title matches have higher weight
        
        # Check snippet
        for keyword, weight in keywords.items():
            if keyword in snippet:
                score += weight
        
        # Add freshness score (newer articles should rank higher)
        if "date" in article and article["date"]:
            try:
                date_str = article["date"]
                if "T" in date_str:
                    date_str = date_str.split("T")[0]
                
                date = datetime.strptime(date_str, "%Y-%m-%d")
                days_ago = (datetime.now() - date).days
                freshness_score = max(10 - days_ago/2, 0)  # Max 10 points for very recent, decreasing over time
                score += freshness_score
            except Exception:
                # If date parsing fails, skip freshness score
                pass
        
        # Add source credibility score (could be expanded with a real source credibility database)
        credible_sources = ["cointelegraph", "coindesk", "decrypt", "theblock", "bloomberg", "forbes", "reuters"]
        source = article.get("source", "").lower()
        
        for credible_source in credible_sources:
            if credible_source in source:
                score += 5
                break
        
        article["relevance_score"] = score
    
    # Sort by score
    return sorted(articles, key=lambda x: x.get("relevance_score", 0), reverse=True)

def rank_with_gemini(articles: List[Dict[str, Any]], max_articles: int = 20, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Rank articles using Google's Gemini model.
    
    Args:
        articles: List of articles to rank
        max_articles: Maximum number of articles to return (default: 20)
        verbose: Whether to print verbose output
        
    Returns:
        List of most relevant articles
    """
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not found. Falling back to keyword ranking.")
        return rank_with_keywords(articles)[:max_articles]
    
    if not GENAI_AVAILABLE:
        print("Google GenerativeAI library not available. Falling back to keyword ranking.")
        return rank_with_keywords(articles)[:max_articles]
    
    try:
        # Prepare data for Gemini
        article_data = []
        for idx, article in enumerate(articles):
            article_data.append({
                "id": idx,
                "title": article.get("title", ""),
                "snippet": article.get("snippet", ""),
                "source": article.get("source", ""),
                "date": article.get("date", "")
            })
        
        # Configure the API key
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Create a model instance (using the latest available model)
        try:
            # Try the latest model first
            model = genai.GenerativeModel('gemini-1.5-flash')
            if verbose:
                print("Using gemini-1.5-flash model")
        except Exception as e:
            print(f"Error initializing gemini-1.5-flash: {e}, falling back to gemini-pro")
            try:
                # Fall back to gemini-pro if 1.5 isn't available
                model = genai.GenerativeModel('gemini-pro')
                if verbose:
                    print("Using gemini-pro model")
            except Exception as e:
                print(f"Error initializing gemini-pro: {e}, falling back to keyword ranking")
                return rank_with_keywords(articles)[:max_articles]
        
        # Prepare prompt
        prompt = f"""You are a cryptocurrency news expert. Your task is to rank the following news articles based on their relevance, importance, and quality.
        
Look for:
1. Important cryptocurrency news like market movements, regulatory changes, or technological advancements
2. Articles from credible sources
3. Recent and timely articles
4. Informative content rather than clickbait

Here are the articles to rank:
{json.dumps(article_data, indent=2)}

Please return a JSON array with EXACTLY {max_articles} IDs of the most relevant articles, ranked from most to least important. 
For example: [4, 12, 7, 2, ...]

You MUST return {max_articles} article IDs, or as many as there are if fewer than {max_articles} are available.
The array should contain only the article IDs, nothing else."""
        
        if verbose:
            print(f"Sending prompt to Gemini:\n{prompt[:300]}...")
        
        # Call Gemini API using the SDK
        try:
            # Set safety settings to be permissive for content analysis
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_ONLY_HIGH"
                }
            ]
            
            # Generate content with safety settings
            response = model.generate_content(
                prompt,
                safety_settings=safety_settings
            )
            
            # Extract JSON array from the response
            generated_text = response.text
            
            if verbose:
                print(f"Gemini response:\n{generated_text[:500]}...")
            
            json_match = re.search(r'\[.*\]', generated_text, re.DOTALL)
            
            if json_match:
                try:
                    ranked_ids = json.loads(json_match.group())
                    
                    if verbose:
                        print(f"Extracted ranked IDs: {ranked_ids}")
                    
                    # Return articles in the ranked order
                    ranked_articles = []
                    for article_id in ranked_ids:
                        if article_id < len(articles):
                            ranked_articles.append(articles[article_id])
                    
                    # If we don't have enough ranked articles, add any remaining ones
                    if len(ranked_articles) < max_articles:
                        if verbose:
                            print(f"Got only {len(ranked_articles)} rankings, adding more to reach {max_articles}")
                        for article in articles:
                            if article not in ranked_articles and len(ranked_articles) < max_articles:
                                ranked_articles.append(article)
                    
                    # If we have too many articles, truncate to max_articles
                    if len(ranked_articles) > max_articles:
                        if verbose:
                            print(f"Truncating from {len(ranked_articles)} to {max_articles} articles")
                        ranked_articles = ranked_articles[:max_articles]
                    
                    return ranked_articles
                except json.JSONDecodeError:
                    print("Could not parse Gemini response as JSON. Falling back to keyword ranking.")
                    if verbose:
                        print(f"Failed to parse: {json_match.group()}")
                    return rank_with_keywords(articles)[:max_articles]
            else:
                print("Could not find a JSON array in Gemini response. Falling back to keyword ranking.")
                return rank_with_keywords(articles)[:max_articles]
                
        except Exception as e:
            print(f"API request error with Gemini: {e}")
            print("Falling back to keyword ranking.")
            return rank_with_keywords(articles)[:max_articles]
    
    except Exception as e:
        print(f"Error ranking articles with Gemini: {e}")
        print("Falling back to keyword ranking.")
        return rank_with_keywords(articles)[:max_articles]

def rank_articles(articles: List[Dict[str, Any]], use_ai: bool = True, max_articles: int = 20, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Rank articles using the best available method.
    
    Args:
        articles: List of articles to rank
        use_ai: Whether to use AI (Gemini) for ranking
        max_articles: Maximum number of articles to return
        verbose: Whether to print verbose output
        
    Returns:
        List of ranked articles
    """
    print(f"Ranking {len(articles)} articles...")
    
    if use_ai and GEMINI_API_KEY:
        print("Using Gemini AI for ranking")
        ranked_articles = rank_with_gemini(articles, max_articles, verbose)
    else:
        print("Using keyword-based ranking")
        ranked_articles = rank_with_keywords(articles)[:max_articles]
    
    print(f"Ranked articles. Top article: {ranked_articles[0].get('title', '') if ranked_articles else 'None'}")
    
    # Save ranked articles to JSON
    output_dir = os.path.join("data", "ranked")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"ranked_articles_{timestamp}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "count": len(ranked_articles),
            "articles": ranked_articles
        }, f, ensure_ascii=False, indent=2)
    
    print(f"Saved ranked articles to {output_file}")
    
    return ranked_articles 