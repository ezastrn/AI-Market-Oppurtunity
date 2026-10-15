import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon

from src.spatial_analysis import add_competition_indicators, create_grid


def test_grid_uses_projected_crs_and_cells_are_valid():
    boundary = gpd.GeoDataFrame(geometry=[Polygon([(0, 0), (1000, 0), (1000, 1000), (0, 1000)])], crs="EPSG:3857")
    grid = create_grid(boundary, 500, .5)
    assert len(grid) == 4
    assert grid.geometry.is_valid.all()


def test_competitor_just_outside_boundary_affects_edge_cell():
    cells = gpd.GeoDataFrame({"cell_id": ["edge"], "inside_fraction": [1]}, geometry=[Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])], crs="EPSG:3857")
    competitors = gpd.GeoDataFrame(geometry=[Point(110, 50)], crs="EPSG:3857")
    result = add_competition_indicators(cells, competitors, 100, 1, (5, 95), {"nearest_competitor_m": .5, "competitor_count": .5})
    assert result.loc[0, "competitor_count"] == 1
    assert result.loc[0, "nearest_competitor_m"] == 60
