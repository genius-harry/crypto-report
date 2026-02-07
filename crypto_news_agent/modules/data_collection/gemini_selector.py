import os
import json
import traceback
import google.generativeai as genai
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TopArticleSelectionResponse(BaseModel):
    """Response model for Gemini article selection."""
    selected_indices: List[int]
    reasoning: str

def get_gemini_api_key():
    """Get Gemini API key directly."""
    # Hardcode the API key directly
    os.environ["GEMINI_API_KEY"] = "AIzaSyBUZhuigNXSH9Asokj-oXbZdNDZO66EH0c"
    
    # Return the hardcoded API key
    return "AIzaSyBUZhuigNXSH9Asokj-oXbZdNDZO66EH0c"

def select_top_articles(articles: List[Dict[str, Any]], top_n: int = 20) -> Tuple[List[Dict[str, Any]], str]:
    """
    Use Gemini to select the top most relevant crypto news articles.
    
    Args:
        articles: List of article dictionaries with title, url, etc.
        top_n: Number of top articles to select
        
    Returns:
        Tuple of (selected_articles, reasoning)
    """
    try:
        # Configure Gemini API
        api_key = get_gemini_api_key()
        print(f"Using Gemini API key: {api_key[:5]}...{api_key[-5:] if len(api_key) > 10 else ''}")
        genai.configure(api_key=api_key)
        
        # Get available models to verify API key works
        try:
            models = genai.list_models()
            model_names = [m.name for m in models]
            print(f"Available Gemini models: {model_names}")
        except Exception as e:
            print(f"Error listing Gemini models (API key may be invalid): {e}")
            raise
            
        # Use the correct model ID
        model_id = "gemini-1.5-flash"  # Updated from 2.0 to 1.5 which is currently available
        print(f"Using Gemini model: {model_id}")
        model = genai.GenerativeModel(model_id)
        
        # Prepare the list of articles for Gemini to evaluate
        article_list_text = ""
        for i, article in enumerate(articles):
            article_list_text += f"{i+1}. {article.get('title', 'No title')}\n"
        
        prompt = (
            "You are an expert cryptocurrency analyst assistant. Below is a list of cryptocurrency news article titles. "
            f"Please select the top {top_n} most valuable and relevant articles for a crypto investor who wants to stay informed about "
            "important market developments, significant price movements, regulatory changes, technological advancements, "
            "and mainstream adoption news. Focus on articles that have actionable insights or important information rather than "
            "clickbait or repetitive content.\n\n"
            f"Article List:\n{article_list_text}\n\n"
            f"Return your response as a JSON object with two keys:\n"
            f"1. 'selected_indices': An array of integers representing the indices of the top {top_n} selected articles (use the article numbers provided)\n"
            f"2. 'reasoning': A brief explanation of your selection criteria\n\n"
        )
        
        # Generate content with JSON output
        print("Sending request to Gemini API...")
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "selected_indices": {
                            "type": "array",
                            "items": {"type": "integer"}
                        },
                        "reasoning": {"type": "string"}
                    },
                    "required": ["selected_indices", "reasoning"]
                }
            }
        )
        
        print("Received response from Gemini API")
        print(f"Response text: {response.text[:100]}...")
        
        # Parse the response
        parsed_response = json.loads(response.text)
        selected_indices = parsed_response.get("selected_indices", [])
        
        # Validate and adjust indices (Gemini might return 1-based indices, we need 0-based)
        selected_indices = [idx - 1 for idx in selected_indices if 0 < idx <= len(articles)]
        
        # Get the selected articles
        selected_articles = [articles[idx] for idx in selected_indices if idx < len(articles)]
        
        # If we don't have enough selected articles, fill with top items
        if len(selected_articles) < top_n:
            missing_count = top_n - len(selected_articles)
            remaining_indices = [i for i in range(len(articles)) if i not in selected_indices]
            additional_articles = [articles[i] for i in remaining_indices[:missing_count]]
            selected_articles.extend(additional_articles)
        
        # Limit to top_n articles
        selected_articles = selected_articles[:top_n]
        
        return selected_articles, parsed_response.get("reasoning", "")
    
    except Exception as e:
        print(f"Error selecting top articles with Gemini: {e}")
        print("Full traceback:")
        traceback.print_exc()
        # Fallback: return first top_n articles
        return articles[:min(top_n, len(articles))], f"Error using Gemini API for selection: {str(e)}"

# Add a test function that can be called independently
def test_gemini(sample_size=5):
    """Test the Gemini API with a small sample of fake articles"""
    print("Testing Gemini API with sample data...")
    
    # Create some sample articles
    sample_articles = [
        {"title": f"Sample Crypto Article {i}", "url": f"https://example.com/{i}"} 
        for i in range(1, sample_size + 1)
    ]
    
    # Try to select top articles
    selected, reasoning = select_top_articles(sample_articles, top_n=3)
    
    print("\nTest Results:")
    print(f"Selected {len(selected)} articles")
    print(f"Reasoning: {reasoning}")
    
    return selected, reasoning

if __name__ == "__main__":
    # Run the test function when the script is executed directly
    test_gemini()