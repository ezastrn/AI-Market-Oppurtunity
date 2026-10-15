# Methodology

## Scope

This is exploratory screening of **mapped** OSM features in Kota Malang. It is not a demand forecast, profitability model, investment recommendation, or verified site-selection result.

## Indicators

| Component | Raw inputs | Favourable direction | Combination |
| --- | --- | --- | --- |
| Competition Gap (CG) | competitor count within radius; nearest mapped competitor distance | fewer competitors; greater distance | Equal-weight combination of normalized inputs |
| Contextual Suitability (CS) | category-specific configured POI counts within radius | more relevant mapped context | Equal-weight combination over available feature types |
| Accessibility (AC) | distance to nearest primary, secondary, or tertiary road | shorter distance | Inverted normalized distance |

All distances and areas use `EPSG:32749` (WGS 84 / UTM zone 49S) after run-time CRS validation. Normalization is winsorized min–max over eligible cells only; high values always mean more favourable. Zero-variance features are excluded and remaining component weights are renormalized.

## Eligibility

A cell must meet the configured boundary fraction and have evidence of built environment (buildings, suitable land use, or road length) while remaining below the excluded-land-use threshold. Ineligible cells appear in neutral styling on the map and are never ranked.

## Sufficiency and robustness

Ranking is permitted only when configured gates for competitor count, eligible-cell count, available score components, and district coverage pass. Radius and weight scenarios are compared against baseline rankings. Evidence labels (`HIGH`, `MEDIUM`, `LOW`) are rule-based and separate from score.

## Data limitations

OSM coverage varies by place and tag. A missing mapped business is not proof that no business exists. Context and road proximity are proxies, not demand measurements. Field observation, competitor verification, rent and zoning checks, and customer research are required before a business decision.
