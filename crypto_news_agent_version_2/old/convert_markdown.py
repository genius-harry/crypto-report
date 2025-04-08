import os
import re
import glob
import shutil    # <-- new import
from datetime import datetime

BASE_MARKDOWN_DIR = "/Users/yiranyao/Documents/Cursor/crypto report/crypto_news_agent_version_1/markdown"

def get_latest_folder(base_dir):
    # List folders matching "news_*"
    folders = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and d.startswith("news_")]
    if not folders:
        raise Exception("No news folders found")
    # Extract datetime from folder name "news_YYYYMMDD_HHMMSS"
    def folder_date(name):
        try:
            return datetime.strptime(name.split('_', 1)[1], "%Y%m%d_%H%M%S")
        except Exception:
            return datetime.min
    latest = max(folders, key=folder_date)
    return os.path.join(base_dir, latest)

def clean_markdown(content):
    # Remove lines containing iframes
    lines = content.splitlines()
    cleaned_lines = []
    for line in lines:
        if "iframe" in line.lower():
            continue
        # Stop processing if we reach a subscriber-only message
        if "Subscribe to continue" in line:
            break
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines)
    # Additional cleanup: remove extra spaces and redundant newlines
    cleaned = re.sub(r'\n{3,}', "\n\n", cleaned)
    return cleaned

def process_markdown_files():
    latest_folder = get_latest_folder(BASE_MARKDOWN_DIR)
    pattern = os.path.join(latest_folder, "*.md")
    md_files = glob.glob(pattern)
    if not md_files:
        print("No markdown files found in:", latest_folder)
        return
    # Remove old "formatted" folder if exists and recreate it
    formatted_folder = os.path.join(BASE_MARKDOWN_DIR, "formatted")
    if os.path.exists(formatted_folder):
        shutil.rmtree(formatted_folder)
    os.makedirs(formatted_folder)
    
    for filepath in md_files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        cleaned_content = clean_markdown(content)
        new_filename = os.path.basename(filepath).replace(".md", "_formatted.md")
        new_filepath = os.path.join(formatted_folder, new_filename)
        with open(new_filepath, "w", encoding="utf-8") as f:
            f.write(cleaned_content)
        print(f"Processed and saved: {new_filepath}")

if __name__ == "__main__":
    process_markdown_files()
