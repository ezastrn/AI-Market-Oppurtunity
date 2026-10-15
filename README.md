# AI Market Opportunity Intelligence

A reproducible, notebook-first geospatial workflow for **preliminary market-opportunity screening** in Kota Malang, East Java, Indonesia.

It uses OpenStreetMap (OSM) data to locate grid cells with relatively low **observed** competitor coverage and relevant surrounding context. It produces traceable indicators, a ranked candidate table, an interactive map, charts, and a structured report.

> A high score does **not** mean demand, revenue, profit, commercial viability, or business success. It only identifies areas worth validating through field research and other evidence.

## What it does

- Retrieves public OSM boundary, business, context, road, building, and land-use data with polite caching.
- Selects a category from configured candidates using a documented coverage rule.
- Cleans, deduplicates, and quality-flags mapped businesses.
- Uses a projected CRS for all local distances and areas.
- Applies a built-environment eligibility filter before ranking cells.
- Scores competition gap, contextual suitability, and road-accessibility proxy.
- Stops with `INSUFFICIENT DATA` if evidence gates fail instead of inventing rankings.
- Tests radius and weighting sensitivity and labels evidence strength separately from opportunity score.

## Project layout

```text
config/       Reproducible analysis settings
data/         Raw snapshots (ignored), processed data, and generated outputs
docs/         PRD review, decisions, feasibility, and methodology
notebooks/    Primary, guided analysis interface
src/          Testable pipeline modules
tests/        Unit and integration tests (synthetic fixtures only)
reports/      Generated market-intelligence reports
```

## Quick start

Python 3.10+ is required. Create an isolated environment, install the pinned dependencies, then run the notebook:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
jupyter lab
```

Open `notebooks/market_opportunity_analysis.ipynb` and run the cells in order. The notebook calls the same modular pipeline used by tests.

The notebook is deliberately the primary execution interface. It validates the configuration before a live run, documents each stage, and directs results to the standard output paths. The first live retrieval stores immutable snapshots plus retrieval metadata under `data/raw/`. Do not commit full raw OSM extracts unless their redistribution obligations have been reviewed.

The pipeline probes the configured Overpass endpoint and documented fallbacks before downloading. If none is healthy or the PRD's data-sufficiency gates fail, it writes a clear `INSUFFICIENT DATA` summary and report without creating misleading candidate rankings. Retry later or provide a documented, lawful cached snapshot.

## Outputs

Successful runs write the following generated artefacts to `data/outputs/`:

- `cleaned_businesses.csv` — traceable cleaned competitor records
- `candidate_ranking.csv` — ranked eligible cells, explanations, and validation prompts
- `cell_scores.csv` — raw indicators, normalized components, and contributions
- `cells.geojson` and `candidates.geojson` — spatial exports
- `opportunity_map.html` — interactive screening map
- `charts/` — data funnel, score distribution, and candidate contributions

If the data-sufficiency gates fail, the run writes an insufficiency summary and deliberately produces no ranked candidates.

## Method and responsible use

The core method is classical spatial analytics, not a machine-learning demand model. It uses OSM as a community-maintained map and never interprets missing OSM features as proof that real businesses are absent. See [methodology](docs/methodology.md), [data feasibility](docs/data_feasibility.md), and the [decision log](docs/decision_log.md) for assumptions and run evidence.

## Data and licences

This repository's source code is available under the [MIT License](LICENSE).

OpenStreetMap data are © OpenStreetMap contributors and are available under the [Open Database License (ODbL)](https://www.openstreetmap.org/copyright). Maps and reports must retain the attribution `© OpenStreetMap contributors`. OSM-derived databases may have additional share-alike obligations under ODbL; this repository excludes raw OSM downloads by default.

## Status

The implementation follows `PRD_AI_Market_Opportunity_Intelligence_v1.1.txt`, which is retained as the project specification. The [PRD review](docs/prd_review.md) records conservative clarifications without silently changing requirements.
