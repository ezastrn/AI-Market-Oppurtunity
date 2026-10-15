# Decision log

| Date | Decision | Reason | Impact |
| --- | --- | --- | --- |
| 2026-10-15 | Use English as the default report language. | PRD OD-1 default; suitable for a portfolio project. | Configurable to Bahasa Indonesia in a future run. |
| 2026-10-15 | Keep raw OSM snapshots out of version control. | OSM data carry ODbL attribution/redistribution obligations; public repository status is not otherwise confirmed. | Retrieval remains reproducible through metadata and code. |
| 2026-10-15 | Use an OSMnx/Overpass-compatible, configurable retrieval layer with caching and backoff. | Matches the recommended stack and supports endpoint changes or cached snapshots. | Live endpoint reachability/policy is verified at run time and recorded in metadata. |
| 2026-10-15 | Retain PRD v1.1 unchanged and document clarifications separately. | The PRD calls itself the single source of truth. | `docs/prd_review.md` makes interpretation auditable. |
