# PRD implementation review

The source PRD is retained unchanged as the project's specification. This review records implementation clarifications; it does not replace the PRD.

| Topic | Clarification used in this repository | Rationale |
| --- | --- | --- |
| Repository name | The GitHub repository spelling is `AI-Market-Oppurtunity`; internal documentation uses the correctly spelled product name. | Keeps the remote URL stable while presenting a professional product name. |
| Report language | English is the default. | This is the PRD default in OD-1; an Indonesian executive summary is deferred. |
| Category choice | The pipeline evaluates configured candidate categories from actual retrieved OSM records before selecting one. | Avoids hardcoding a category or inventing coverage facts. |
| Candidate zones | Adjacent-cell grouping is documented as a future `SHOULD` enhancement; MVP exports stable top cells and explicitly warns of clustering. | The PRD permits this conservative MVP treatment. |
| Public data | Raw OSM downloads are ignored by Git; only retrieval code, metadata schema, and small synthetic tests are committed. | Avoids accidental redistribution and preserves reproducibility. |
| OSM endpoint policy | Retrieval code uses a configurable endpoint, an identifying User-Agent, request timeout, retry/backoff, and a local cache. | Supports polite public-data access; operators must still review the current provider policy before a live run. |

## Non-negotiable interpretation

An opportunity score measures low **observed OSM** competitor coverage plus contextual and accessibility proxies within eligible built-up cells. It does not measure demand, revenue, profitability, zoning approval, or commercial viability. Every generated report and map repeats this limitation.
