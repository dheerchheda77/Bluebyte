import pytest
from .kdtree import KDTree
from .pathfinding import OceanGrid
from .clustering import identify_pfz_zones

def test_kdtree():
    tree = KDTree()
    points = [
        (10.0, 10.0, "A"), (10.1, 10.1, "B"), (10.2, 10.2, "C"),
        (20.0, 20.0, "D"), (20.1, 20.1, "E"), (20.2, 20.2, "F"),
        (30.0, 30.0, "G"), (30.1, 30.1, "H"), (30.2, 30.2, "I"),
        (40.0, 40.0, "J")
    ]
    tree.build_from_points(points)
    
    res = tree.nearest((10.05, 10.05), k=1)
    assert res[0][1] in ["A", "B"]
    
    res = tree.range_query((10.0, 10.0), 50)
    assert len(res) == 3

def test_pathfinding():
    grid = OceanGrid(lat_min=10.0, lat_max=20.0, lon_min=70.0, lon_max=80.0, resolution=1.0)
    route, cost = grid.find_route(11.0, 71.0, 18.0, 78.0, use_currents=False)
    assert len(route) > 0
    assert route[0] == (11.0, 71.0)
    assert route[-1] == (18.0, 78.0)

def test_clustering():
    sample_obs = [
        {'lat': 15.0, 'lon': 73.0, 'sst': 28.5, 'chlorophyll_a': 2.5},
        {'lat': 15.1, 'lon': 73.1, 'sst': 28.3, 'chlorophyll_a': 2.8},
        {'lat': 15.2, 'lon': 73.0, 'sst': 28.4, 'chlorophyll_a': 2.1},
        {'lat': 15.3, 'lon': 73.0, 'sst': 28.5, 'chlorophyll_a': 1.8},
        {'lat': 10.0, 'lon': 70.0, 'sst': 20.0, 'chlorophyll_a': 0.5},
    ]
    zones = identify_pfz_zones(sample_obs)
    assert len(zones) == 1
    assert zones[0]['num_points'] == 4
