#!/bin/bash
# Setup: venv + dependencies + directories + .env bootstrap.
# Idempotent: safe to re-run.

set -euo pipefail

cd "$(dirname "$0")"

# ---- 1. virtualenv ----------------------------------------------------------
if [ ! -d "venv" ]; then
    echo ">>> Creating virtual environment (venv/)"
    python3 -m venv venv
else
    echo ">>> venv/ already exists"
fi

# shellcheck disable=SC1091
source venv/bin/activate

# ---- 2. dependencies --------------------------------------------------------
echo ">>> Upgrading pip"
python -m pip install --upgrade pip --quiet

echo ">>> Installing requirements.txt"
pip install -r requirements.txt

# ---- 3. runtime directories -------------------------------------------------
echo ">>> Ensuring runtime directories exist"
mkdir -p data/search_results data/articles data/ranked
mkdir -p markdown/formatted
mkdir -p output/pdf
mkdir -p static templates

# ---- 4. .env bootstrap ------------------------------------------------------
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "!!! Created .env from .env.example."
    echo "!!! Edit .env and fill in at minimum OPENAI_API_KEY and NEO4J_PASSWORD"
    echo ""
fi

# ---- 5. Docker / Neo4j hint -------------------------------------------------
echo ""
echo "Setup complete."
echo ""
if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is NOT installed. To start Neo4j:"
    echo "  1. Install Docker Desktop:  https://www.docker.com/products/docker-desktop/"
    echo "     or Colima:                brew install colima docker docker-compose && colima start"
    echo "  2. docker compose up -d"
else
    echo "Next: start Neo4j"
    echo "  docker compose up -d"
    echo ""
    echo "Then run the pipeline:"
    echo "  source venv/bin/activate"
    echo "  ./run_graphrag.sh                   # full pipeline"
    echo "  python main.py --only-graph         # rebuild graph from cached articles"
    echo "  python main.py --only-web           # just the web UI"
fi
