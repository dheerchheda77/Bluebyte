"""
seed_data.py — Postgres-native replacement for the SQLite version.

Same synthetic-data intent as the original, adapted to the new schema:
  * ocean_grids / fishing_zones / alerts get real geography points
  * buoy readings are inserted THROUGH etl_pipeline.OutlierPreservingETL
    instead of raw INSERTs, and a handful are deliberately seeded as
    extreme outliers (a marine-heatwave-style SST spike, a hypoxia-style
    DO crash) so you can demo the anomaly flagging live and confirm
    those rows are flagged, not dropped or smoothed.
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg

from db.connection import DATABASE_URL, db_manager
from db.etl_pipeline import OutlierPreservingETL, compute_h3_index

INDIA_LAT_RANGE = (5.0, 25.0)
INDIA_LON_RANGE = (65.0, 95.0)


async def seed_ocean_grids(conn):
    grids = []
    for i in range(20):
        lat_base = random.uniform(*INDIA_LAT_RANGE)
        lon_base = random.uniform(*INDIA_LON_RANGE)
        # Simple 1x1 degree box polygon, WKT
        polygon_wkt = (
            f"POLYGON(({lon_base} {lat_base}, {lon_base+1} {lat_base}, "
            f"{lon_base+1} {lat_base+1}, {lon_base} {lat_base+1}, {lon_base} {lat_base}))"
        )
        grids.append((f"GRID-{i:03d}", f"Area {i}", polygon_wkt))

    await conn.executemany(
        """
        INSERT INTO ocean_grids (grid_code, area_name, geom)
        VALUES ($1, $2, ST_SetSRID(ST_GeomFromText($3), 4326)::geography)
        ON CONFLICT (grid_code) DO NOTHING
        """,
        grids,
    )
    print(f"Seeded {len(grids)} ocean grids")


async def seed_species(conn):
    species = [
        ("Indian Mackerel", "Rastrelliger kanagurta", "Scombridae", "Pelagic", "Least Concern", 26.0, 31.0, 33.0, 36.0, 0, 100, "High"),
        ("Oil Sardine", "Sardinella longiceps", "Clupeidae", "Pelagic", "Least Concern", 27.0, 30.5, 33.5, 35.5, 0, 50, "High"),
        ("Hilsa", "Tenualosa ilisha", "Clupeidae", "Anadromous", "Least Concern", 25.0, 30.0, 10.0, 34.0, 0, 50, "Very High"),  # wide salinity range: anadromous
        ("Bombay Duck", "Harpadon nehereus", "Synodontidae", "Demersal", "Least Concern", 24.0, 29.0, 32.0, 35.0, 10, 200, "Medium"),
        ("Yellowfin Tuna", "Thunnus albacares", "Scombridae", "Pelagic", "Near Threatened", 20.0, 30.0, 34.0, 36.5, 0, 250, "Very High"),
        ("Penaeid Shrimp", "Penaeus indicus", "Penaeidae", "Benthic", "Least Concern", 26.0, 32.0, 30.0, 35.0, 5, 80, "High"),
    ]
    await conn.executemany(
        """
        INSERT INTO species (common_name, scientific_name, family, habitat_type,
                              conservation_status, min_sst, max_sst, min_salinity,
                              max_salinity, min_depth, max_depth, commercial_value)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
        """,
        species,
    )
    print(f"Seeded {len(species)} species")
    return await conn.fetch("SELECT id FROM species")


async def seed_edna_samples(conn, species_ids):
    samples = []
    for i in range(15):
        lat = random.uniform(*INDIA_LAT_RANGE)
        lon = random.uniform(*INDIA_LON_RANGE)
        samples.append((
            f"EDNA-{i:04d}",
            random.choice(species_ids)["id"],
            lat, lon,
            compute_h3_index(lat, lon),
            random.choice(["COI", "12S", "16S"]),
            "ACTG" * random.randint(10, 20),
            random.uniform(0.7, 0.99),
            datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30)),
        ))
    await conn.executemany(
        """
        INSERT INTO edna_samples (sample_id, species_id, geom, h3_index, marker_gene,
                                   sequence_fragment, detection_confidence, collection_date)
        VALUES ($1, $2, ST_SetSRID(ST_MakePoint($4, $3), 4326)::geography, $5, $6, $7, $8, $9)
        ON CONFLICT (sample_id) DO NOTHING
        """,
        samples,
    )
    print(f"Seeded {len(samples)} eDNA samples")


async def seed_buoy_readings(etl: OutlierPreservingETL, n_normal: int = 80, n_outliers: int = 5):
    """Seeds normal readings plus a handful of deliberate outliers
    (marine-heatwave-style SST spikes, hypoxia-style DO crashes) so the
    outlier flagging can be demoed against known-injected anomalies.

    Uses only 4 sensors (not 10) so each accumulates ~20 baseline
    readings before any outlier is scored — MAD-based scoring needs a
    reasonable sample size per sensor (the ETL requires >=5 combined
    points before it will score at all); spreading readings across too
    many sensors leaves some with too little history, which is what
    caused missed/false-positive flags in the first seeding run."""
    sensor_ids = [f"BUOY-{i}" for i in range(1, 5)]
    now = datetime.now(timezone.utc)

    normal_rows = []
    for _ in range(n_normal):
        ts = now - timedelta(hours=random.randint(1, 72))
        normal_rows.append({
            "sensor_id": random.choice(sensor_ids),
            "ts": ts,
            "lat": random.uniform(*INDIA_LAT_RANGE),
            "lon": random.uniform(*INDIA_LON_RANGE),
            "sst": random.uniform(27.0, 30.0),          # normal SST band
            "salinity": random.uniform(33.5, 35.0),
            "chlorophyll_a": random.uniform(0.1, 5.0),
            "dissolved_oxygen": random.uniform(5.5, 8.0),  # normal DO band
            "wave_height": random.uniform(0.5, 3.0),
            "current_velocity": random.uniform(0.1, 2.0),
            "current_direction": random.uniform(0, 360),
        })

    outlier_rows = []
    for i in range(n_outliers):
        ts = now - timedelta(hours=random.randint(1, 72))
        is_heatwave = i % 2 == 0
        outlier_rows.append({
            "sensor_id": random.choice(sensor_ids),
            "ts": ts,
            "lat": random.uniform(*INDIA_LAT_RANGE),
            "lon": random.uniform(*INDIA_LON_RANGE),
            "sst": random.uniform(34.0, 37.0) if is_heatwave else random.uniform(27.0, 30.0),
            "salinity": random.uniform(33.5, 35.0),
            "chlorophyll_a": random.uniform(0.1, 5.0),
            "dissolved_oxygen": random.uniform(1.0, 2.5) if not is_heatwave else random.uniform(5.5, 8.0),  # hypoxia crash
            "wave_height": random.uniform(0.5, 3.0),
            "current_velocity": random.uniform(0.1, 2.0),
            "current_direction": random.uniform(0, 360),
        })

    # Ingest normal rows first so there's a baseline for the outlier
    # rows to actually score against.
    result_normal = await etl.ingest_buoy_batch(normal_rows)
    result_outliers = await etl.ingest_buoy_batch(outlier_rows)

    print(f"Seeded {result_normal.accepted} normal buoy readings "
          f"({result_normal.flagged_outliers} unexpectedly flagged)")
    print(f"Seeded {result_outliers.accepted} deliberate-outlier buoy readings "
          f"({result_outliers.flagged_outliers} correctly flagged as anomalies)")


async def seed_fishing_zones(conn):
    zones = []
    now = datetime.now(timezone.utc)
    for i in range(5):
        zones.append((
            f"PFZ-{i+1}",
            random.uniform(*INDIA_LAT_RANGE), random.uniform(*INDIA_LON_RANGE),
            random.uniform(10.0, 50.0), random.uniform(0.7, 0.99),
            random.choice(["Indian Mackerel", "Yellowfin Tuna", "Oil Sardine"]),
            now, now + timedelta(days=3),
        ))
    await conn.executemany(
        """
        INSERT INTO fishing_zones (zone_name, geom, radius_km, pfz_score,
                                    dominant_species, valid_from, valid_until)
        VALUES ($1, ST_SetSRID(ST_MakePoint($3, $2), 4326)::geography, $4, $5, $6, $7, $8)
        """,
        zones,
    )
    print(f"Seeded {len(zones)} fishing zones")


async def seed_alerts(conn):
    now = datetime.now(timezone.utc)
    alerts = [
        ("SST Anomaly", "High", "BUOY-3", 12.5, 75.2, "Sudden temperature spike detected.", now - timedelta(hours=2), False),
        ("Low Oxygen", "Critical", "BUOY-7", 10.1, 76.5, "Dissolved oxygen dropped below critical threshold.", now - timedelta(hours=5), False),
        ("Equipment Failure", "Medium", "BUOY-1", 15.0, 72.0, "Sensor connection lost.", now - timedelta(hours=10), True),
    ]
    await conn.executemany(
        """
        INSERT INTO alerts (alert_type, severity, sensor_id, geom, message, created_at, acknowledged)
        VALUES ($1, $2, $3, ST_SetSRID(ST_MakePoint($5, $4), 4326)::geography, $6, $7, $8)
        """,
        alerts,
    )
    print(f"Seeded {len(alerts)} alerts")


async def seed_data():
    print(f"Seeding database at {DATABASE_URL}")
    pool = await db_manager.connect()
    etl = OutlierPreservingETL(pool)

    async with pool.acquire() as conn:
        await seed_ocean_grids(conn)
        species_ids = await seed_species(conn)
        await seed_edna_samples(conn, species_ids)
        await seed_fishing_zones(conn)
        await seed_alerts(conn)

    await seed_buoy_readings(etl)  # goes through the ETL, not a raw connection

    print("Database seeding completed.")


# Alias for start.py compatibility
seed_all = seed_data

if __name__ == "__main__":
    asyncio.run(seed_data())