import math
from dataclasses import dataclass
from typing import List, Tuple, Any, Optional

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0 # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@dataclass
class KDNode:
    point: Tuple[float, float]
    data: Any
    left: Optional['KDNode'] = None
    right: Optional['KDNode'] = None

class KDTree:
    def __init__(self):
        self.root = None

    def insert(self, point: Tuple[float, float], data: Any = None):
        def _insert(node: Optional[KDNode], depth: int) -> KDNode:
            if node is None:
                return KDNode(point, data)
            cd = depth % 2
            if point[cd] < node.point[cd]:
                node.left = _insert(node.left, depth + 1)
            else:
                node.right = _insert(node.right, depth + 1)
            return node
        self.root = _insert(self.root, 0)

    def nearest(self, query_point: Tuple[float, float], k: int = 1) -> List[Tuple[float, Any]]:
        best = [] # list of (dist, data, point)

        def _search(node: Optional[KDNode], depth: int):
            if node is None:
                return
            
            dist = haversine(query_point[0], query_point[1], node.point[0], node.point[1])
            
            # Keep sorted best list, size <= k
            best.append((dist, node.data, node.point))
            best.sort(key=lambda x: x[0])
            if len(best) > k:
                best.pop()

            cd = depth % 2
            # Calculate distance along the axis for bounding box check
            # Approx 111km per degree
            axis_diff = query_point[cd] - node.point[cd]
            
            if axis_diff < 0:
                first, second = node.left, node.right
            else:
                first, second = node.right, node.left

            _search(first, depth + 1)
            
            axis_dist_km = abs(axis_diff) * 111.0 
            if len(best) < k or axis_dist_km < best[-1][0]:
                _search(second, depth + 1)
        
        _search(self.root, 0)
        return [(b[0], b[1]) for b in best]

    def range_query(self, center: Tuple[float, float], radius_km: float) -> List[Tuple[float, float, Any]]:
        results = []
        def _search(node: Optional[KDNode], depth: int):
            if node is None:
                return
            
            dist = haversine(center[0], center[1], node.point[0], node.point[1])
            if dist <= radius_km:
                results.append((node.point[0], node.point[1], node.data))
                
            cd = depth % 2
            axis_diff = center[cd] - node.point[cd]
            
            if axis_diff < 0:
                _search(node.left, depth + 1)
                if abs(axis_diff) * 111.0 <= radius_km:
                    _search(node.right, depth + 1)
            else:
                _search(node.right, depth + 1)
                if abs(axis_diff) * 111.0 <= radius_km:
                    _search(node.left, depth + 1)
                    
        _search(self.root, 0)
        return results

    def build_from_points(self, points_list: List[Tuple[float, float, Any]]):
        for lat, lon, data in points_list:
            self.insert((lat, lon), data)

if __name__ == "__main__":
    tree = KDTree()
    points = [
        (15.4, 73.8, "Goa"),
        (13.5, 74.5, "Fishing Zone A"),
        (14.0, 74.0, "Buoy 1"),
        (12.0, 75.0, "Cluster 1")
    ]
    tree.build_from_points(points)
    print("Nearest to (15.0, 73.0):", tree.nearest((15.0, 73.0), k=2))
    print("Within 200km from (14.0, 74.0):", tree.range_query((14.0, 74.0), 200))
