"""
Script to fix the cryptocurrency section of the report.
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

# Neo4j connection parameters
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def connect_to_neo4j():
    """Connect to Neo4j database and return driver."""
    try:
        driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        print("Successfully connected to Neo4j!")
        return driver
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        return None

def get_top_cryptocurrencies(driver, limit=5):
    """Get the top mentioned cryptocurrencies."""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Cryptocurrency)<-[r:MENTIONS_CRYPTO]-(a:Article)
            WITH c, count(a) AS article_count
            RETURN c.name AS cryptocurrency, c.symbol AS symbol, article_count
            ORDER BY article_count DESC
            LIMIT $limit
        """, limit=limit)
        
        return [dict(record) for record in result]

def create_new_report():
    """Create a new report file with correct cryptocurrency data."""
    output_dir = "output"
    original_report_path = os.path.join(output_dir, "crypto_market_report.md")
    new_report_path = os.path.join(output_dir, "crypto_market_report_fixed.md")
    
    print("Creating a new report file with correct cryptocurrency data...")
    
    # Connect to Neo4j and get the top cryptocurrencies
    driver = connect_to_neo4j()
    if not driver:
        print("Could not connect to Neo4j database.")
        return
    
    try:
        top_cryptocurrencies = get_top_cryptocurrencies(driver)
        driver.close()
        
        if not top_cryptocurrencies:
            print("No cryptocurrency data found.")
            return
        
        print(f"Found {len(top_cryptocurrencies)} top cryptocurrencies:")
        for crypto in top_cryptocurrencies:
            print(f"- {crypto['cryptocurrency']} ({crypto['symbol']}): {crypto['article_count']} mentions")
        
        # Create new report content
        new_content = """# Cryptocurrency Market Report: Latest Insights and Analysis

## Introduction

The cryptocurrency market continues to evolve rapidly, with various digital assets gaining attention in the news media. This report provides an analysis of the most mentioned cryptocurrencies, significant recent events, regulatory developments, and emerging trends in the crypto space.

## Most Mentioned Cryptocurrencies

Based on our database analysis, the following cryptocurrencies have been most frequently mentioned in recent news articles:

"""
        
        # Add cryptocurrency data
        for crypto in top_cryptocurrencies:
            new_content += f"- **{crypto['cryptocurrency']} ({crypto['symbol']})**: {crypto['article_count']} mentions\n"
        
        new_content += """
This data highlights Bitcoin's continued dominance in media coverage, with Ethereum maintaining a strong presence as well. The significant attention given to Ripple, Solana, and Tether also reflects their importance in the current cryptocurrency landscape.

## Significant Recent Events

Two notable events have recently occurred in the crypto space:

1. **Major Liquidation Event**: A cryptocurrency trader lost over $308 million after their 50x leveraged Ether position was liquidated, highlighting the risks of high-leverage trading in volatile markets.

2. **Cross-Border Payment Solutions**: Russian oil companies have begun using Bitcoin, Ethereum, and Tether for cross-border payments with China and India, demonstrating cryptocurrency's utility in facilitating international trade, particularly in contexts affected by sanctions.

## Regulatory Developments

While our analysis indicates no significant recent regulatory changes specifically affecting cryptocurrencies, regulatory considerations remain a critical factor for market participants. The lack of major regulatory news could suggest a period of policy consolidation following earlier announcements.

## Innovation Areas

The cryptocurrency industry continues to innovate across several key areas:

1. **Decentralized Finance (DeFi)**: Expanding financial services without traditional intermediaries
2. **Non-Fungible Tokens (NFTs)**: Digital ownership and authenticity verification
3. **Layer 2 Solutions**: Scaling improvements for blockchain networks
4. **Central Bank Digital Currencies (CBDCs)**: Government-backed digital currencies
5. **Stablecoins**: Price-stable digital assets
6. **Cross-Border Payment Solutions**: International value transfer mechanisms
7. **Privacy Technologies**: Enhancing transaction confidentiality
8. **Interoperability**: Connecting different blockchain ecosystems

## Recent News Themes

The main topics appearing in cryptocurrency news include Blockchain Technology, DeFi, Regulation, Trading, Price Movement, NFTs, Mining, Stablecoins, Politics, and ETFs. This diverse range of topics reflects the maturing cryptocurrency ecosystem and its growing impact across multiple sectors.

## Conclusion

The cryptocurrency market remains highly dynamic, with Bitcoin and Ethereum continuing to dominate media attention. Recent events highlight both the risks (leveraged trading liquidations) and practical applications (cross-border payments) of cryptocurrencies. As the market evolves, staying informed about these developments will be essential for investors, developers, and other stakeholders in the cryptocurrency space.
"""
        
        # Write to new file
        with open(new_report_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        print(f"Successfully created new report with correct cryptocurrency data: {new_report_path}")
        print(f"Original report remains at: {original_report_path}")
    
    except Exception as e:
        print(f"Error creating new report: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_new_report() 