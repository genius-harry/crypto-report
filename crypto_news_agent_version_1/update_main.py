#!/usr/bin/env python
"""
Update main.py with new command-line options
"""

import argparse
import re

def update_parse_args():
    """Update the parse_arguments function to include --only-scrape option"""
    
    with open("main.py", "r") as f:
        content = f.read()
    
    # Find the parser.add_argument lines
    parser_pattern = r"(def parse_arguments\(\).*?)(\s+return parser\.parse_args\(\))"
    parser_match = re.search(parser_pattern, content, re.DOTALL)
    
    if not parser_match:
        print("Could not find parse_arguments function")
        return False
    
    current_parser = parser_match.group(1)
    return_line = parser_match.group(2)
    
    # Add the new option for --only-scrape
    new_option = """
    # Add options for running individual phases
    parser.add_argument("--only-scrape", action="store_true", help="Only run phase 3: Scrape news")
    """
    
    # Combine the function with the new option
    updated_parser = current_parser + new_option + return_line
    
    # Replace the old function with the updated one
    updated_content = content.replace(parser_match.group(0), updated_parser)
    
    # Write the updated content back to main.py
    with open("main.py", "w") as f:
        f.write(updated_content)
    
    print("Added --only-scrape option to main.py")
    return True

if __name__ == "__main__":
    update_parse_args() 