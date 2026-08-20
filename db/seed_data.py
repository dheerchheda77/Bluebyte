import asyncio
import random
from datetime import datetime, timedelta
import aiosqlite
import os

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.connection import get_db, DB_PATH

async def seed_data():
    print(f"Seeding database at {DB_PATH}")
    async with get_db() as db:
        # Seed Ocean Grids (Arabian Sea, Bay of Bengal, Lakshadweep, Andaman)
        grids = []
        for i in range(20):
            # Rough bounding boxes for India coastal waters
            lat_base = random.uniform(5.0, 25.0)
            lon_base = random.uniform(65.0, 95.0)
            grid = (
                f"GRID-{i:03d}",
                lat_base, lat_base + 1.0,
                lon_base, lon_base + 1.0,
                f"Area {i}"
            )
            grids.append(grid)
            
        await db.executemany("""
            INSERT INTO ocean_grids (grid_code, lat_min, lat_max, lon_min, lon_max, area_name)
            VALUES (?, ?, ?, ?, ?, ?)
        """, grids)
        
        # Seed Species
        species = [
            ("Indian Mackerel", "Rastrelliger kanagurta", "Scombridae", "Pelagic", "Least Concern", 26.0, 31.0, 0, 100, "High"),
            ("Oil Sardine", "Sardinella longiceps", "Clupeidae", "Pelagic", "Least Concern", 27.0, 30.5, 0, 50, "High"),
            ("Hilsa", "Tenualosa ilisha", "Clupeidae", "Anadromous", "Least Concern", 25.0, 30.0, 0, 50, "Very High"),
            ("Bombay Duck", "Harpadon nehereus", "Synodontidae", "Demersal", "Least Concern", 24.0, 29.0, 10, 200, "Medium"),
            ("Yellowfin Tuna", "Thunnus albacares", "Scombridae", "Pelagic", "Near Threatened", 20.0, 30.0, 0, 250, "Very High"),
            ("Penaeid Shrimp", "Penaeus indicus", "Penaeidae", "Benthic", "Least Concern", 26.0, 32.0, 5, 80, "High")
        ]
        
        await db.executemany("""
            INSERT INTO species (common_name, scientific_name, family, habitat_type, conservation_status, min_sst, max_sst, min_depth, max_depth, commercial_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, species)

        # Seed eDNA Samples
        edna_samples = []
        for i in range(15):
            edna_samples.append((
                f"EDNA-{i:04d}",
                random.randint(1, 6),
                random.randint(1, 20),
                random.choice(["COI", "12S", "16S"]),
                "ACTG" * random.randint(10, 20),
                random.uniform(0.7, 0.99),
                (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat()
            ))
            
        await db.executemany("""
            INSERT INTO edna_samples (sample_id, species_id, grid_id, marker_gene, sequence_fragment, detection_confidence, collection_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, edna_samples)

        # Seed Buoy Readings
        readings = []
        for i in range(50):
            timestamp = datetime.now() - timedelta(hours=random.randint(1, 72))
            readings.append((
                f"BUOY-{random.randint(1, 10)}",
                timestamp.isoformat(),
                random.uniform(5.0, 25.0),
                random.uniform(65.0, 95.0),
                random.uniform(25.0, 32.0),
                random.uniform(32.0, 36.0),
                random.uniform(0.1, 5.0),
                random.uniform(4.0, 8.0),
                random.uniform(0.5, 3.0),
                random.uniform(0.1, 2.0),
                random.uniform(0, 360),
                0, "", 0.0, 0.0
            ))
            
        await db.executemany("""
            INSERT INTO buoy_readings (sensor_id, timestamp, lat, lon, sst, salinity, chlorophyll_a, dissolved_oxygen, wave_height, current_velocity, current_direction, anomaly_flag, anomaly_reason, z_score_sst, z_score_do)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, readings)

        # Seed Fishing Zones
        zones = []
        for i in range(5):
            now = datetime.now()
            zones.append((
                f"PFZ-{i+1}",
                random.uniform(5.0, 25.0),
                random.uniform(65.0, 95.0),
                random.uniform(10.0, 50.0),
                random.uniform(0.7, 0.99),
                random.choice(["Indian Mackerel", "Yellowfin Tuna", "Oil Sardine"]),
                now.isoformat(),
                (now + timedelta(days=3)).isoformat()
            ))
            
        await db.executemany("""
            INSERT INTO fishing_zones (zone_name, center_lat, center_lon, radius_km, pfz_score, dominant_species, valid_from, valid_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, zones)

        # Seed Alerts
        alerts = [
            ("SST Anomaly", "High", "BUOY-3", 12.5, 75.2, "Sudden temperature spike detected.", (datetime.now() - timedelta(hours=2)).isoformat(), 0),
            ("Low Oxygen", "Critical", "BUOY-7", 10.1, 76.5, "Dissolved oxygen dropped below critical threshold.", (datetime.now() - timedelta(hours=5)).isoformat(), 0),
            ("Equipment Failure", "Medium", "BUOY-1", 15.0, 72.0, "Sensor connection lost.", (datetime.now() - timedelta(hours=10)).isoformat(), 1)
        ]
        
        await db.executemany("""
            INSERT INTO alerts (alert_type, severity, sensor_id, lat, lon, message, created_at, acknowledged)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, alerts)

        await db.commit()
    print("Database seeding completed.")

# Alias for start.py compatibility
seed_all = seed_data

if __name__ == "__main__":
    asyncio.run(seed_data())
