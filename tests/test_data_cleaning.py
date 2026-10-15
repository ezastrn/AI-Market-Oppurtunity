import geopandas as gpd
from shapely.geometry import Point, Polygon

from src.data_cleaning import clean_businesses


def test_cleaning_removes_invalid_outside_and_merges_named_near_duplicates():
    boundary = gpd.GeoDataFrame(geometry=[Polygon([(112.60, -7.99), (112.62, -7.99), (112.62, -7.97), (112.60, -7.97)])], crs="EPSG:4326")
    records = gpd.GeoDataFrame(
        {"feature_id": ["node/1", "node/1", "node/2", "node/3", "node/4", "way/5"],
         "name": ["Cafe A", "Cafe A", "Cafe A", None, "Outside", "Cafe Polygon"]},
        geometry=[Point(112.61, -7.98), Point(112.61, -7.98), Point(112.6101, -7.9801), Point(112.611, -7.981), Point(112.70, -7.90), Polygon([(112.612, -7.982), (112.613, -7.982), (112.613, -7.981), (112.612, -7.981)])],
        crs="EPSG:4326",
    )
    cleaned, summary = clean_businesses(records, boundary, "cafe", "EPSG:32749", 30)
    assert summary == {"retrieved": 6, "invalid_removed": 0, "outside_boundary": 1, "duplicates_merged": 2, "retained": 3}
    assert set(cleaned["geometry_type"]) == {"point", "polygon"}
    assert "missing_name" in cleaned.loc[cleaned["name"].isna(), "data_quality_flag"].iloc[0]


def test_unnamed_nearby_records_are_retained():
    boundary = gpd.GeoDataFrame(geometry=[Polygon([(112.60, -7.99), (112.62, -7.99), (112.62, -7.97), (112.60, -7.97)])], crs="EPSG:4326")
    records = gpd.GeoDataFrame({"feature_id": ["node/1", "node/2"], "name": [None, None]}, geometry=[Point(112.61, -7.98), Point(112.61001, -7.98001)], crs="EPSG:4326")
    cleaned, summary = clean_businesses(records, boundary, "cafe", "EPSG:32749")
    assert len(cleaned) == 2
    assert summary["duplicates_merged"] == 0
