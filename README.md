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

## Quick start

```bash
# 1. Install Docker Desktop (or Colima): https://www.docker.com/products/docker-desktop/
# 2. Clone, then:
./setup.sh                                    # venv + deps + .env from template
$EDITOR .env                                  # fill in OPENAI_API_KEY at minimum
docker compose up -d                          # starts Neo4j on :7474 (UI) and :7687 (bolt)
source venv/bin/activate
python main.py --only-graph                   # build graph from cached articles
python main.py --only-report                  # generate report
python main.py --only-web                     # serve UI on http://localhost:5001
```

## Setup (detailed)

### 1. Python deps

```bash
./setup.sh           # creates venv + installs requirements.txt + bootstraps .env
# or manually:
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Environment variables

Edit `.env`. Defaults match `docker-compose.yml`.

| Var | Required? | Used by |
|---|---|---|
| `OPENAI_API_KEY` | **yes** | ranker + report generator |
| `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` | **yes** | graph + report |
| `SERP_API_KEY` | no — falls back to cached results | search |
| `GEMINI_API_KEY` | no — falls back to keyword scoring | ranker |
| `FIRECRAWL_API_KEY` | no — falls back to per-site crawlers | scraper |
| `COINAPI_KEY` | no | optional market metadata enrichment |

### 3. Neo4j (via Docker)

```bash
docker compose up -d         # starts cryptoreport-neo4j (Neo4j 5.20 + APOC)
docker compose logs -f       # tail logs
docker compose down          # stop
docker compose down -v       # stop + delete volumes (wipes graph)
```

Browser UI: <http://localhost:7474> (login with the user/password from `.env`).

Alternative backends, if you don't want Docker:
- **Neo4j Desktop**: create a local DB, use its bolt URL + password
- **Neo4j AuraDB**: cloud, set `NEO4J_URI=neo4j+s://...`

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

## Custom crawlers

`modules/data_collection/custom_crawlers/crawler_controller.py` invokes
per-site crawler scripts in `<site>/run_*.sh`. Each script creates its
own local venv (under `<site>/venv/`) and pulls just the deps it needs,
so crawlers stay isolated. The controller maps:

| Crawler | Method | Extra deps |
|---|---|---|
| `beincrypto` | RSS | feedparser |
| `cointelegraph` | RSS | feedparser |
| `utoday` | HTTP + BS4 | (covered by base) |
| `bitcoin` | Selenium | **needs Chrome + chromedriver** |
| `coindesk` | Selenium | **needs Chrome + webdriver-manager** |
| `cryptonews` | Selenium | **needs Chrome + undetected-chromedriver** |

The three Selenium-based crawlers need a working Chrome browser on the
host. Without it, the crawler subprocess will fail; the pipeline keeps
going (it just collects fewer fresh articles). For RSS-based sites this
is not a concern. To smoke-test:

```bash
python -c "from modules.data_collection.custom_crawlers.crawler_controller import run_crawler; run_crawler('beincrypto', max_articles=2)"
```

## Troubleshooting

**`Connection refused` on bolt://localhost:7687** — Neo4j isn't running.
`docker compose up -d`. Wait ~30s for it to be ready, then retry.

**`Did not find username, please add an environment variable NEO4J_USERNAME`** —
your `.env` is missing or not loaded. `cp .env.example .env` and fill it in.

**`401 Unauthorized` from OpenAI** — `OPENAI_API_KEY` in `.env` is missing or
invalid.

**Chat in web UI returns nothing** — Neo4j is empty. Run
`python main.py --only-graph` first to populate it.

**`Module not found: markdown2` / `firecrawl_py` / `langchain_neo4j`** — install
deps in the activated venv: `pip install -r requirements.txt`.

**`docker compose up` fails on `apoc` plugin** — wait a minute on first run;
Neo4j downloads the plugin into `./neo4j_plugins/`. Subsequent starts are
instant.

## License

MIT.
