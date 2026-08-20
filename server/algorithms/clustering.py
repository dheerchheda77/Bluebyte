import math
from typing import List, Dict, Any, Tuple

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class DBSCAN:
    def __init__(self, eps_km: float, min_samples: int):
        self.eps = eps_km
        self.min_samples = min_samples

    def fit_predict(self, data: List[Dict[str, float]]) -> List[int]:
        n = len(data)
        labels = [-1] * n
        cluster_id = 0
        
        def region_query(idx):
            neighbors = []
            for i in range(n):
                if haversine(data[idx]['lat'], data[idx]['lon'], data[i]['lat'], data[i]['lon']) <= self.eps:
                    neighbors.append(i)
            return neighbors
            
        for i in range(n):
            if labels[i] != -1:
                continue
                
            neighbors = region_query(i)
            if len(neighbors) < self.min_samples:
                labels[i] = -2 
                continue
                
            cluster_id += 1
            labels[i] = cluster_id
            
            seed_set = list(neighbors)
            seed_set.remove(i)
            
            while seed_set:
                q = seed_set.pop(0)
                if labels[q] == -2:
                    labels[q] = cluster_id
                if labels[q] != -1:
                    continue
                    
                labels[q] = cluster_id
                q_neighbors = region_query(q)
                
                if len(q_neighbors) >= self.min_samples:
                    for n_idx in q_neighbors:
                        if labels[n_idx] == -1 or labels[n_idx] == -2:
                            seed_set.append(n_idx)
                            
        return labels

def identify_pfz_zones(observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = []
    for obs in observations:
        if 26 <= obs.get('sst', 0) <= 30 and obs.get('chlorophyll_a', 0) > 1.5:
            filtered.append(obs)
            
    if not filtered:
        return []
        
    dbscan = DBSCAN(eps_km=50, min_samples=3)
    labels = dbscan.fit_predict(filtered)
    
    clusters = {}
    for obs, label in zip(filtered, labels):
        if label > 0:
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(obs)
            
    pfz_zones = []
    for cluster_id, points in clusters.items():
        avg_sst = sum(p['sst'] for p in points) / len(points)
        avg_chl = sum(p['chlorophyll_a'] for p in points) / len(points)
        
        lats = [p['lat'] for p in points]
        lons = [p['lon'] for p in points]
        
        centroid = (sum(lats) / len(points), sum(lons) / len(points))
        bbox = {
            'min_lat': min(lats),
            'max_lat': max(lats),
            'min_lon': min(lons),
            'max_lon': max(lons)
        }
        
        score = score_zone(avg_sst, avg_chl, len(points))
        
        pfz_zones.append({
            'centroid': centroid,
            'bounding_box': bbox,
            'avg_sst': avg_sst,
            'avg_chlorophyll_a': avg_chl,
            'num_points': len(points),
            'pfz_score': score
        })
        
    return pfz_zones
    
def score_zone(avg_sst: float, avg_chlorophyll: float, num_points: int) -> float:
    sst_score = 1.0 - abs(28.0 - avg_sst) / 2.0  
    chl_score = min(avg_chlorophyll / 5.0, 1.0)  
    size_score = min(num_points / 20.0, 1.0)
    
    score = (sst_score * 0.4) + (chl_score * 0.4) + (size_score * 0.2)
    return max(0.0, min(1.0, score))

if __name__ == "__main__":
    sample_obs = [
        {'lat': 15.0, 'lon': 73.0, 'sst': 28.5, 'chlorophyll_a': 2.5},
        {'lat': 15.1, 'lon': 73.1, 'sst': 28.3, 'chlorophyll_a': 2.8},
        {'lat': 15.2, 'lon': 73.0, 'sst': 28.4, 'chlorophyll_a': 2.1},
        {'lat': 15.3, 'lon': 73.0, 'sst': 28.5, 'chlorophyll_a': 1.8},
        {'lat': 10.0, 'lon': 70.0, 'sst': 20.0, 'chlorophyll_a': 0.5},
        {'lat': 12.0, 'lon': 74.0, 'sst': 27.5, 'chlorophyll_a': 3.0},
        {'lat': 12.1, 'lon': 74.1, 'sst': 27.2, 'chlorophyll_a': 3.2},
        {'lat': 12.0, 'lon': 74.2, 'sst': 27.8, 'chlorophyll_a': 3.5}
    ]
    
    zones = identify_pfz_zones(sample_obs)
    for i, z in enumerate(zones):
        print(f"Zone {i+1}: Score={z['pfz_score']:.2f}, Centroid={z['centroid']}, Size={z['num_points']}")
