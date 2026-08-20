import math
from typing import List, Tuple, Optional
from dataclasses import dataclass
import heapq

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def bearing(lat1, lon1, lat2, lon2):
    lat1, lon1 = math.radians(lat1), math.radians(lon1)
    lat2, lon2 = math.radians(lat2), math.radians(lon2)
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
    initial_bearing = math.atan2(x, y)
    initial_bearing = math.degrees(initial_bearing)
    return (initial_bearing + 360) % 360

@dataclass
class GridCell:
    current_velocity: float # knots
    current_direction: float # degrees
    is_land: bool

class OceanGrid:
    def __init__(self, lat_min=5.0, lat_max=25.0, lon_min=65.0, lon_max=95.0, resolution=0.5):
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.lon_min = lon_min
        self.lon_max = lon_max
        self.resolution = resolution
        
        self.lats = int((lat_max - lat_min) / resolution) + 1
        self.lons = int((lon_max - lon_min) / resolution) + 1
        
        self.grid = [[GridCell(0.0, 0.0, False) for _ in range(self.lons)] for _ in range(self.lats)]
        self.generate_sample_currents()
        
    def _latlon_to_idx(self, lat, lon):
        r = int(round((lat - self.lat_min) / self.resolution))
        c = int(round((lon - self.lon_min) / self.resolution))
        return r, c
        
    def _idx_to_latlon(self, r, c):
        lat = self.lat_min + r * self.resolution
        lon = self.lon_min + c * self.resolution
        return lat, lon

    def generate_sample_currents(self):
        import random
        random.seed(42)
        for r in range(self.lats):
            for c in range(self.lons):
                lat, lon = self._idx_to_latlon(r, c)
                if lat > 20 and lon > 70:
                    self.grid[r][c].is_land = True
                elif lat > 15 and lon > 73:
                    if random.random() < 0.2:
                        self.grid[r][c].is_land = True
                
                self.grid[r][c].current_velocity = random.uniform(0.5, 2.5) 
                self.grid[r][c].current_direction = (180 + (lat - 15) * 10) % 360

    def find_route(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float, use_currents=True) -> Tuple[List[Tuple[float, float]], float]:
        start_idx = self._latlon_to_idx(start_lat, start_lon)
        end_idx = self._latlon_to_idx(end_lat, end_lon)
        
        if self.grid[start_idx[0]][start_idx[1]].is_land or self.grid[end_idx[0]][end_idx[1]].is_land:
            raise ValueError("Start or End is on land")
            
        max_boat_speed = 10.0 
        
        open_set = []
        heapq.heappush(open_set, (0, start_idx))
        
        came_from = {}
        g_score = {start_idx: 0}
        
        def h(idx):
            lat, lon = self._idx_to_latlon(*idx)
            return haversine(lat, lon, end_lat, end_lon)
            
        while open_set:
            current_f, current = heapq.heappop(open_set)
            
            if current == end_idx:
                path = []
                curr = current
                while curr in came_from:
                    path.append(self._idx_to_latlon(*curr))
                    curr = came_from[curr]
                path.append(self._idx_to_latlon(*start_idx))
                return path[::-1], g_score[current]
                
            r, c = current
            neighbors = []
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0: continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.lats and 0 <= nc < self.lons:
                        if not self.grid[nr][nc].is_land:
                            neighbors.append((nr, nc))
                            
            for neighbor in neighbors:
                clat, clon = self._idx_to_latlon(*current)
                nlat, nlon = self._idx_to_latlon(*neighbor)
                
                dist = haversine(clat, clon, nlat, nlon)
                cell = self.grid[r][c]
                
                if use_currents:
                    head = bearing(clat, clon, nlat, nlon)
                    heading_diff = abs(head - cell.current_direction)
                    if heading_diff > 180:
                        heading_diff = 360 - heading_diff
                        
                    current_factor = math.cos(math.radians(heading_diff))
                    effective_speed = max_boat_speed + cell.current_velocity * current_factor
                    if effective_speed <= 0: effective_speed = 0.1
                    cost = dist / effective_speed
                else:
                    cost = dist / max_boat_speed
                
                tentative_g = g_score[current] + cost
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    heapq.heappush(open_set, (tentative_g + h(neighbor) / max_boat_speed, neighbor))
                    
        return [], 0.0

    def compute_fuel_savings(self, cost_with_currents: float, cost_without: float) -> float:
        if cost_without == 0: return 0.0
        return ((cost_without - cost_with_currents) / cost_without) * 100.0

if __name__ == "__main__":
    grid = OceanGrid()
    start = (15.4, 73.8) # Goa
    end = (13.5, 74.5)   # Fishing Zone
    
    route_with, cost_with = grid.find_route(*start, *end, use_currents=True)
    route_without, cost_without = grid.find_route(*start, *end, use_currents=False)
    
    print(f"Cost with currents: {cost_with:.2f}")
    print(f"Cost without currents: {cost_without:.2f}")
    print(f"Savings: {grid.compute_fuel_savings(cost_with, cost_without):.2f}%")
