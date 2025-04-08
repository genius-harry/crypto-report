"""
Markdown to GraphRAG

This script loads cryptocurrency news from markdown files into Neo4j,
builds a GraphRAG system, and generates a comprehensive report.
"""

import os
import re
import glob
from datetime import datetime
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph
from langchain_neo4j import GraphCypherQAChain

# Load environment variables
load_dotenv()

# Neo4j connection parameters
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "Yaoyiran20061111"

# OpenAI API key from .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Markdown directory
MARKDOWN_DIR = "markdown/formatted"

def connect_to_neo4j():
    """Establish connection to Neo4j database."""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        # Verify connection
        with driver.session() as session:
            result = session.run("RETURN 1 AS test")
            for record in result:
                print(f"Neo4j connection test: {record['test']}")
        print("Successfully connected to Neo4j!")
        return driver
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        return None

def setup_schema(driver):
    """Set up Neo4j schema with constraints and indexes."""
    with driver.session() as session:
        # Create constraints
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Article) REQUIRE a.title IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Cryptocurrency) REQUIRE c.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Source) REQUIRE s.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE")
        
        # Create additional indexes
        session.run("CREATE INDEX IF NOT EXISTS FOR (a:Article) ON (a.date)")
        
        print("Neo4j schema setup complete!")

def extract_cryptocurrency_mentions(text):
    """Extract cryptocurrency mentions from text."""
    # List of common cryptocurrencies and their variations
    crypto_dict = {
        'Bitcoin': ['Bitcoin', 'BTC', 'XBT', 'bitcoin'],
        'Ethereum': ['Ethereum', 'ETH', 'Ether', 'ethereum'],
        'Ripple': ['Ripple', 'XRP', 'ripple'],
        'Solana': ['Solana', 'SOL', 'solana'],
        'Tether': ['Tether', 'USDT', 'tether'],
        'Binance Coin': ['Binance Coin', 'BNB', 'binance coin'],
        'Cardano': ['Cardano', 'ADA', 'cardano'],
        'Dogecoin': ['Dogecoin', 'DOGE', 'dogecoin'],
        'USD Coin': ['USD Coin', 'USDC', 'usd coin'],
        'Litecoin': ['Litecoin', 'LTC', 'litecoin'],
        'Chainlink': ['Chainlink', 'LINK', 'chainlink'],
        'Polkadot': ['Polkadot', 'DOT', 'polkadot']
    }
    
    found_cryptos = []
    
    for crypto_name, variations in crypto_dict.items():
        for variation in variations:
            pattern = r'\b' + re.escape(variation) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                found_cryptos.append({
                    'name': crypto_name,
                    'symbol': variations[1] if len(variations) > 1 else variations[0]
                })
                break  # Only add each crypto once
                
    return found_cryptos

def extract_topics(text):
    """Extract relevant topics from text."""
    topics_dict = {
        'ETF': ['ETF', 'Exchange-Traded Fund', 'exchange-traded fund', 'Exchange Traded Fund'],
        'Regulation': ['regulation', 'regulatory', 'SEC', 'lawsuit', 'legal', 'compliance'],
        'Price Movement': ['price', 'rally', 'surge', 'drop', 'increase', 'decrease', 'all-time high', 'ATH'],
        'Federal Reserve': ['Fed', 'Federal Reserve', 'interest rate', 'rate decision', 'Jerome Powell'],
        'Trading': ['trading', 'exchange', 'market', 'trader', 'volume', 'liquidity'],
        'DeFi': ['DeFi', 'decentralized finance', 'yield farming', 'staking', 'liquidity pool'],
        'NFT': ['NFT', 'non-fungible token', 'digital art', 'collectible'],
        'Mining': ['mining', 'miner', 'hash rate', 'proof of work', 'PoW'],
        'Stablecoins': ['stablecoin', 'USDT', 'USDC', 'DAI', 'pegged'],
        'Blockchain Technology': ['blockchain', 'protocol', 'layer-2', 'scaling', 'smart contract'],
        'Institutional Adoption': ['institutional', 'corporate', 'adoption', 'investment firm', 'fund', 'hedge fund'],
        'Politics': ['Trump', 'Biden', 'administration', 'president', 'election', 'political']
    }
    
    found_topics = []
    
    for topic_name, variations in topics_dict.items():
        for variation in variations:
            pattern = r'\b' + re.escape(variation) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                found_topics.append(topic_name)
                break  # Only add each topic once
                
    return found_topics

def extract_people(text):
    """Extract people mentioned in the text using regex patterns."""
    # Pattern for names - looking for capitalized words possibly with titles
    name_pattern = r'(?:Mr\.|Ms\.|Mrs\.|Dr\.|Prof\.)?\s?([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)'
    
    # Find all matches
    matches = re.findall(name_pattern, text)
    
    # Filter out common false positives
    false_positives = ['ETF', 'Bitcoin', 'Ethereum', 'Solana', 'Ripple', 'Federal Reserve',
                        'SEC', 'Tether', 'United States', 'Federal Reserve']
    
    people = []
    for match in matches:
        if match not in false_positives and not any(fp in match for fp in false_positives):
            people.append(match.strip())
    
    return list(set(people))  # Remove duplicates

def parse_markdown_file(file_path):
    """Parse a markdown file and extract relevant information."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
            # Extract title - usually the first heading
            title_match = re.search(r'^#\s(.+)$', content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else os.path.basename(file_path)
            
            # Extract source URL
            source_match = re.search(r'Source:\s(https?://[^\s]+)', content)
            source_url = source_match.group(1) if source_match else ""
            
            # Extract source name from URL
            source_name = ""
            if source_url:
                domain_match = re.search(r'https?://(?:www\.)?([^/]+)', source_url)
                if domain_match:
                    domain = domain_match.group(1)
                    # Extract the main part of the domain (e.g., 'livemint' from 'livemint.com')
                    source_name = domain.split('.')[0] if '.' in domain else domain
            
            # Extract date
            date_match = re.search(r'Updated\s?(\d+\s[A-Za-z]+\s\d{4})', content)
            date = date_match.group(1) if date_match else ""
            
            # Extract author
            author_match = re.search(r'\*\*([^*]+)\*\*', content)
            author = author_match.group(1).strip() if author_match else ""
            
            # Extract cryptocurrency mentions
            crypto_mentions = extract_cryptocurrency_mentions(content)
            
            # Extract topics
            topics = extract_topics(content)
            
            # Extract people mentioned
            people = extract_people(content)
            
            # Use content as summary, removing markdown syntax
            summary = re.sub(r'##+\s', '', content)
            summary = re.sub(r'\*\*|\*', '', summary)
            summary = re.sub(r'!\[.*?\]\(.*?\)', '', summary)
            summary = re.sub(r'\[.*?\]\(.*?\)', '', summary)
            summary = ' '.join(summary.split())[:1000] + '...'  # Truncate to 1000 chars
            
            return {
                'title': title,
                'source_url': source_url,
                'source_name': source_name,
                'date': date,
                'author': author,
                'crypto_mentions': crypto_mentions,
                'topics': topics,
                'people': people,
                'summary': summary,
                'file_path': file_path
            }
            
    except Exception as e:
        print(f"Error parsing file {file_path}: {e}")
        return None

def load_markdown_files():
    """Load all markdown files from the specified directory."""
    markdown_files = glob.glob(os.path.join(MARKDOWN_DIR, "*.md"))
    print(f"Found {len(markdown_files)} markdown files")
    
    articles = []
    for file_path in markdown_files:
        article_data = parse_markdown_file(file_path)
        if article_data:
            articles.append(article_data)
    
    print(f"Processed {len(articles)} articles")
    return articles

def import_to_neo4j(driver, articles):
    """Import processed articles into Neo4j."""
    print(f"Importing {len(articles)} articles to Neo4j...")
    
    # Clear existing data if needed
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    
    # Import articles in batches
    batch_size = 5
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(articles)-1)//batch_size + 1}")
        
        for article in batch:
            with driver.session() as session:
                # Create Article node
                session.run("""
                    MERGE (a:Article {title: $title})
                    SET a.source_url = $source_url,
                        a.date = $date,
                        a.summary = $summary,
                        a.file_path = $file_path
                """, {
                    'title': article['title'],
                    'source_url': article['source_url'],
                    'date': article['date'],
                    'summary': article['summary'],
                    'file_path': article['file_path']
                })
                
                # Create Source node and relationship
                if article['source_name']:
                    session.run("""
                        MATCH (a:Article {title: $title})
                        MERGE (s:Source {name: $source_name})
                        MERGE (a)-[:FROM]->(s)
                    """, {
                        'title': article['title'],
                        'source_name': article['source_name']
                    })
                
                # Create Author node and relationship if available
                if article['author']:
                    session.run("""
                        MATCH (a:Article {title: $title})
                        MERGE (p:Person {name: $author})
                        MERGE (a)-[:AUTHORED_BY]->(p)
                    """, {
                        'title': article['title'],
                        'author': article['author']
                    })
                
                # Create Cryptocurrency nodes and relationships
                for crypto in article['crypto_mentions']:
                    session.run("""
                        MATCH (a:Article {title: $title})
                        MERGE (c:Cryptocurrency {name: $name})
                        SET c.symbol = $symbol
                        MERGE (a)-[:MENTIONS]->(c)
                    """, {
                        'title': article['title'],
                        'name': crypto['name'],
                        'symbol': crypto['symbol']
                    })
                
                # Create Topic nodes and relationships
                for topic in article['topics']:
                    session.run("""
                        MATCH (a:Article {title: $title})
                        MERGE (t:Topic {name: $topic})
                        MERGE (a)-[:DISCUSSES]->(t)
                    """, {
                        'title': article['title'],
                        'topic': topic
                    })
                
                # Create Person nodes and relationships for mentioned people
                for person in article['people']:
                    session.run("""
                        MATCH (a:Article {title: $title})
                        MERGE (p:Person {name: $person})
                        MERGE (a)-[:MENTIONS_PERSON]->(p)
                    """, {
                        'title': article['title'],
                        'person': person
                    })
    
    # Create additional relationships
    with driver.session() as session:
        # Create relationships between cryptocurrencies mentioned in the same article
        session.run("""
            MATCH (a:Article)-[:MENTIONS]->(c1:Cryptocurrency)
            MATCH (a)-[:MENTIONS]->(c2:Cryptocurrency)
            WHERE c1 <> c2
            MERGE (c1)-[r:RELATED_TO]-(c2)
            ON CREATE SET r.common_articles = 1
            ON MATCH SET r.common_articles = r.common_articles + 1
        """)
        
        # Create relationships between topics discussed in the same article
        session.run("""
            MATCH (a:Article)-[:DISCUSSES]->(t1:Topic)
            MATCH (a)-[:DISCUSSES]->(t2:Topic)
            WHERE t1 <> t2
            MERGE (t1)-[r:RELATED_TOPIC]->(t2)
            ON CREATE SET r.common_articles = 1
            ON MATCH SET r.common_articles = r.common_articles + 1
        """)
    
    print("Data import complete!")

def run_analytics(driver):
    """Run analytics queries on the graph."""
    with driver.session() as session:
        # Count nodes by type
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] AS type, COUNT(*) AS count
            ORDER BY count DESC
        """)
        print("\nNode counts:")
        for record in result:
            print(f"  {record['type']}: {record['count']}")
        
        # Find top mentioned cryptocurrencies
        result = session.run("""
            MATCH (c:Cryptocurrency)<-[r:MENTIONS]-(a:Article)
            RETURN c.name AS name, c.symbol AS symbol, COUNT(r) AS mentions
            ORDER BY mentions DESC
            LIMIT 10
        """)
        print("\nTop mentioned cryptocurrencies:")
        for record in result:
            print(f"  {record['name']} ({record['symbol']}): {record['mentions']} mentions")
        
        # Find top topics
        result = session.run("""
            MATCH (t:Topic)<-[r:DISCUSSES]-(a:Article)
            RETURN t.name AS topic, COUNT(r) AS articles
            ORDER BY articles DESC
            LIMIT 10
        """)
        print("\nTop topics:")
        for record in result:
            print(f"  {record['topic']}: {record['articles']} articles")
        
        # Find strongest cryptocurrency relationships
        result = session.run("""
            MATCH (c1:Cryptocurrency)-[r:RELATED_TO]-(c2:Cryptocurrency)
            RETURN c1.name AS crypto1, c2.name AS crypto2, r.common_articles AS strength
            ORDER BY strength DESC
            LIMIT 8
        """)
        print("\nStrongest cryptocurrency relationships:")
        for record in result:
            print(f"  {record['crypto1']} - {record['crypto2']}: mentioned together in {record['strength']} articles")

def setup_graphrag():
    """Set up the GraphRAG system."""
    # Create LLM instance (can use a smaller model for graph construction)
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    
    try:
        # Connect to Neo4j
        graph = Neo4jGraph(
            url=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database="neo4j"
        )
        
        # Create QA chain
        chain = GraphCypherQAChain.from_llm(
            llm=llm,
            graph=graph,
            verbose=True,
            allow_dangerous_requests=True
        )
        
        return chain
    except Exception as e:
        print(f"Error setting up GraphRAG: {e}")
        return None

def generate_report(chain):
    """Generate a comprehensive report on crypto news."""
    print("\nGenerating crypto news report...")
    
    # Connect to Neo4j directly for some queries
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    # Collect insights from direct queries
    insights = {}
    
    with driver.session() as session:
        # Get top cryptocurrencies
        result = session.run("""
            MATCH (c:Cryptocurrency)<-[r:MENTIONS]-(a:Article)
            RETURN c.name AS name, c.symbol AS symbol, COUNT(r) AS mentions
            ORDER BY mentions DESC
            LIMIT 5
        """)
        top_cryptos = [dict(record) for record in result]
        insights["top_cryptocurrencies"] = top_cryptos
        
        # Get price trends info - limit to top 3 cryptos
        price_trends = []
        for crypto in top_cryptos[:3]:  # Only process top 3
            result = session.run("""
                MATCH (a:Article)-[:MENTIONS]->(c:Cryptocurrency {name: $name})
                WHERE a.title CONTAINS "price" OR a.summary CONTAINS "price"
                OR a.title CONTAINS "surge" OR a.summary CONTAINS "surge"
                OR a.title CONTAINS "rally" OR a.summary CONTAINS "rally"
                OR a.title CONTAINS "drop" OR a.summary CONTAINS "drop"
                RETURN a.title
                LIMIT 2
            """, {"name": crypto["name"]})
            articles = [dict(record) for record in result]
            if articles:
                price_trends.append({
                    "cryptocurrency": crypto["name"],
                    "articles": articles
                })
        insights["price_trends"] = price_trends
        
        # Get regulatory info - titles only
        result = session.run("""
            MATCH (a:Article)-[:DISCUSSES]->(t:Topic)
            WHERE t.name = 'Regulation'
            RETURN a.title
            LIMIT 3
        """)
        regulatory_articles = [dict(record) for record in result]
        insights["regulatory"] = regulatory_articles
        
        # Get ETF info - titles only
        result = session.run("""
            MATCH (a:Article)-[:DISCUSSES]->(t:Topic)
            WHERE t.name = 'ETF'
            RETURN a.title
            LIMIT 3
        """)
        etf_articles = [dict(record) for record in result]
        insights["etf"] = etf_articles
        
        # Get institutional adoption info - titles only
        result = session.run("""
            MATCH (a:Article)-[:DISCUSSES]->(t:Topic)
            WHERE t.name = 'Institutional Adoption'
            RETURN a.title
            LIMIT 3
        """)
        institutional_articles = [dict(record) for record in result]
        insights["institutional"] = institutional_articles
    
    # For final report generation, use a powerful model
    report_llm = ChatOpenAI(model="gpt-4", temperature=0)
    
    # Generate the final report with truncated data
    prompt = f"""
    You are a cryptocurrency analyst tasked with creating a concise report (approximately 500 words) 
    on the latest cryptocurrency news and developments. Use the following information to create your report:
    
    Top Cryptocurrencies (name, symbol, mentions):
    {insights["top_cryptocurrencies"]}
    
    Price Trends Articles for top cryptocurrencies:
    {insights["price_trends"]}
    
    Regulatory Article Titles:
    {insights["regulatory"]}
    
    ETF Article Titles:
    {insights["etf"]}
    
    Institutional Adoption Article Titles:
    {insights["institutional"]}
    
    Focus on the major trends, significant price movements, regulatory updates, new product launches (especially ETFs), and 
    institutional developments. The report should be well-structured with appropriate headings and provide 
    valuable insights for cryptocurrency investors and enthusiasts.
    """
    
    try:
        report_response = report_llm.invoke(prompt)
        final_report = report_response.content
        
        print("\nCrypto News Report Generated!")
        return final_report
    except Exception as e:
        print(f"Error generating report: {e}")
        
        # Fallback to a simpler report
        try:
            simple_prompt = f"""
            Create a brief cryptocurrency market report (500 words) based on these facts:
            - Most mentioned cryptocurrencies: {[f"{c['name']} ({c['symbol']})" for c in insights["top_cryptocurrencies"]]}
            - Main topics discussed: Regulation, ETFs, Price Movements, Institutional Adoption
            - ETF developments for Solana
            - Bitcoin price nearing $86,000
            - SEC dropping lawsuit against Ripple Labs
            """
            
            simple_response = report_llm.invoke(simple_prompt)
            return simple_response.content
        except Exception as e2:
            print(f"Error with fallback report: {e2}")
            return "Error generating report."

def main():
    """Main function to build GraphRAG from markdown files and generate a report."""
    print("Markdown to GraphRAG - Crypto News Analysis")
    print("===========================================\n")
    
    # Connect to Neo4j
    driver = connect_to_neo4j()
    if not driver:
        print("Failed to connect to Neo4j. Please make sure Neo4j is running with the correct credentials.")
        return
    
    # Set up Neo4j schema
    setup_schema(driver)
    
    # Load markdown files
    articles = load_markdown_files()
    if not articles:
        print("No valid articles found!")
        driver.close()
        return
    
    # Import to Neo4j
    import_to_neo4j(driver, articles)
    
    # Run analytics
    run_analytics(driver)
    
    # Set up GraphRAG
    print("\nSetting up GraphRAG system...")
    chain = setup_graphrag()
    if not chain:
        print("Failed to set up GraphRAG system.")
        driver.close()
        return
    
    # Generate report
    report = generate_report(chain)
    print("\nCRYPTO MARKET REPORT:")
    print("=====================")
    print(report)
    
    # Save report to file
    report_file = "crypto_market_report.md"
    with open(report_file, "w") as f:
        f.write("# Cryptocurrency Market Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%B %d, %Y')}\n\n")
        f.write(report)
    
    print(f"\nReport saved to {report_file}")
    
    # Close connection
    driver.close()
    print("\nNeo4j connection closed.")

if __name__ == "__main__":
    main() 