# Data feasibility

## Status: pending first live retrieval

The category-selection rule and boundary verification must be evaluated from real OSM data, not assumed from the PRD. The pipeline therefore writes this evidence during its first successful run:

1. Boundary relation, administrative level, retrieval timestamp, geometry validity, and area comparison with the approximately 110 km² city sanity check.
2. Raw and cleaned counts for each configured candidate category.
3. District coverage for categories meeting the minimum-record rule.
4. Building, land-use, and road-coverage distributions used to set or retain eligibility thresholds.
5. Selected category, tie-break rationale, and any permitted override.

No category or candidate area is claimed in the repository before that evidence exists.
