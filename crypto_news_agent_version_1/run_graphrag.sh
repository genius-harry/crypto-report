#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Run the main script with appropriate arguments
echo "Running Crypto News GraphRAG System..."
python main.py --clean "$@"

# Usage:
# ./run_graphrag.sh                     # Run with default settings
# ./run_graphrag.sh --search            # Run with new search
# ./run_graphrag.sh --skip-graph        # Skip graph building
# ./run_graphrag.sh --search --skip-web # Search but skip web interface 