# Crypto Report

A multi-source crypto news intelligence pipeline. It searches and scrapes
articles from major crypto news sites, builds a Neo4j knowledge graph,
generates a market report via GraphRAG (LangChain + OpenAI), and serves a
Flask web UI for chat / visualization / PDF export.

## Pipeline (6 phases)

```
search → rank → scrape → graph → report → web
```

1. **Search** — Google / SerpAPI news search for crypto topics
2. **Rank** — keyword scoring + optional Gemini LLM ranker
3. **Scrape** — Firecrawl (if API key set) or per-site custom crawlers
4. **Graph** — Neo4j knowledge graph (Article / Cryptocurrency / Topic / Person)
5. **Report** — GraphRAG-generated markdown report
6. **Web** — Flask UI with chat, graph viz, PDF export

Phases can be run individually or skipped. Intermediate state is cached on
disk so partial reruns are cheap.

## Directory layout

```
.
├── main.py                      # entry point — orchestrates all 6 phases
├── run_graphrag.sh              # convenience wrapper around main.py
├── setup.sh                     # installs Python deps
├── requirements.txt
├── .env.example                 # copy to .env and fill in keys
│
├── modules/                     # core pipeline code
│   ├── data_collection/         #   search, rank, scrape
│   │   └── custom_crawlers/     #     dispatcher to per-site crawlers
│   ├── graph_builder/           #   Neo4j ingestion + schema
│   ├── report_generator/        #   GraphRAG chain + report assembly
│   └── web_interface/           #   Flask app, PDF export, templates
│
├── lib/                         # shared utilities
├── templates/                   # Flask Jinja templates
├── static/                      # web assets (graph viz, css/js)
│
├── data/                        # cached intermediate state
│   ├── search_results/
│   ├── ranked/
│   └── articles/                #   ~110 historical scraped articles (fixtures)
├── markdown/                    # human-readable scraped articles
├── output/                      # generated reports + PDFs
├── demos/                       # standalone demo scripts
│
├── beincrypto.com/              # per-site crawlers (called by custom_crawlers)
├── bitcoin.com/
├── coindesk.com/
├── cointelegraph.com/
├── cryptonews.com/
├── theblock.co/
├── u.today/
│
└── try_new_scrawl/              # experimental BS4/Selenium crawlers (not wired in)
```

## Setup

### 1. Python deps

```bash
./setup.sh           # creates venv + installs requirements.txt
# or manually:
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment variables

```bash
cp .env.example .env
# edit .env, fill in at minimum OPENAI_API_KEY and NEO4J_PASSWORD
```

| Var | Required? | Used by |
|---|---|---|
| `OPENAI_API_KEY` | **yes** | ranker + report generator |
| `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` | **yes** | graph + report |
| `SERP_API_KEY` | no — falls back to cached results | search |
| `GEMINI_API_KEY` | no — falls back to keyword scoring | ranker |
| `FIRECRAWL_API_KEY` | no — falls back to per-site crawlers | scraper |
| `COINAPI_KEY` | no | optional market metadata enrichment |

### 3. Neo4j

The repo expects a Neo4j instance reachable at `$NEO4J_URI`
(default `bolt://localhost:7687`). The recommended way is via Docker —
a `docker-compose.yml` is added in Phase B of this rebuild.

For now, options:
- **Neo4j Desktop**: create a local DB, use its bolt URL + password
- **Neo4j AuraDB**: use the cloud bolt URI + credentials
- **Docker (manual)**: `docker run -p 7687:7687 -p 7474:7474 -e NEO4J_AUTH=neo4j/cryptoreport neo4j:5`

## Usage

### Full pipeline

```bash
python main.py
```

### Single phase

```bash
python main.py --only-search    # just search
python main.py --only-rank      # just rank
python main.py --only-scrape    # just scrape
python main.py --only-graph     # just build graph
python main.py --only-report    # just generate report
python main.py --only-web       # just start web UI
```

### Skip phase

```bash
python main.py --skip-graph     # everything except graph
python main.py --skip-web       # everything except web UI
```

### Common flags

```bash
python main.py --query "bitcoin ethereum etf"   # custom search query
python main.py --limit 20                       # process N articles
python main.py --search                         # force fresh search (ignore cache)
python main.py --clean                          # wipe Neo4j before importing
python main.py --verbose                        # extra logging
```

The web UI defaults to <http://localhost:5001>.

## Troubleshooting

**`Did not find username, please add an environment variable NEO4J_USERNAME`** —
your `.env` is missing or not loaded. `cp .env.example .env` and fill it in.

**Chat in web UI returns nothing** — Neo4j is empty. Run
`python main.py --only-graph` first to populate it.

**`Module not found: firecrawl_py` / `langchain_neo4j`** — install deps:
`pip install -r requirements.txt`.

## License

MIT.
