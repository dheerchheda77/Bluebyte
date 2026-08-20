import math
from datetime import datetime, timedelta
from db.connection import get_db

async def get_buoy_readings(sensor_id: str, limit: int = 100):
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM buoy_readings WHERE sensor_id = ? ORDER BY timestamp DESC LIMIT ?",
            (sensor_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_readings_in_area(lat: float, lon: float, radius_km: float, hours: int = 24):
    # Very crude approximation: 1 degree is roughly 111km
    deg_diff = radius_km / 111.0
    lat_min, lat_max = lat - deg_diff, lat + deg_diff
    lon_min, lon_max = lon - deg_diff, lon + deg_diff
    
    time_limit = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    async with get_db() as db:
        async with db.execute("""
            SELECT * FROM buoy_readings 
            WHERE lat BETWEEN ? AND ? 
            AND lon BETWEEN ? AND ?
            AND timestamp >= ?
            ORDER BY timestamp DESC
        """, (lat_min, lat_max, lon_min, lon_max, time_limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_species_for_conditions(sst: float, salinity: float = None):
    # Currently only filtering by SST
    async with get_db() as db:
        async with db.execute("""
            SELECT * FROM species 
            WHERE ? BETWEEN min_sst AND max_sst
        """, (sst,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_edna_detections(grid_id: int):
    async with get_db() as db:
        async with db.execute("""
            SELECT e.*, s.common_name, s.scientific_name 
            FROM edna_samples e
            JOIN species s ON e.species_id = s.id
            WHERE e.grid_id = ?
            ORDER BY e.collection_date DESC
        """, (grid_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_active_alerts():
    async with get_db() as db:
        async with db.execute("""
            SELECT * FROM alerts WHERE acknowledged = 0 ORDER BY created_at DESC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_fishing_zones():
    now = datetime.now().isoformat()
    async with get_db() as db:
        async with db.execute("""
            SELECT * FROM fishing_zones 
            WHERE valid_from <= ? AND valid_until >= ?
            ORDER BY pfz_score DESC
        """, (now, now)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def insert_buoy_reading(data: dict):
    async with get_db() as db:
        await db.execute("""
            INSERT INTO buoy_readings 
            (sensor_id, timestamp, lat, lon, sst, salinity, chlorophyll_a, dissolved_oxygen, wave_height, current_velocity, current_direction, anomaly_flag, anomaly_reason, z_score_sst, z_score_do)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('sensor_id'), data.get('timestamp'), data.get('lat'), data.get('lon'),
            data.get('sst'), data.get('salinity'), data.get('chlorophyll_a'), data.get('dissolved_oxygen'),
            data.get('wave_height'), data.get('current_velocity'), data.get('current_direction'),
            data.get('anomaly_flag', 0), data.get('anomaly_reason', ''), data.get('z_score_sst', 0.0), data.get('z_score_do', 0.0)
        ))
        await db.commit()

async def insert_alert(data: dict):
    async with get_db() as db:
        await db.execute("""
            INSERT INTO alerts (alert_type, severity, sensor_id, lat, lon, message, created_at, acknowledged)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('alert_type'), data.get('severity'), data.get('sensor_id'), 
            data.get('lat'), data.get('lon'), data.get('message'), 
            data.get('created_at', datetime.now().isoformat()), data.get('acknowledged', 0)
        ))
        await db.commit()

async def get_all_species():
    async with get_db() as db:
        async with db.execute("SELECT * FROM species") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_grid_by_coordinates(lat: float, lon: float):
    async with get_db() as db:
        async with db.execute("""
            SELECT * FROM ocean_grids 
            WHERE ? BETWEEN lat_min AND lat_max
            AND ? BETWEEN lon_min AND lon_max
            LIMIT 1
        """, (lat, lon)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
