"""
BlueByte AI — Ocean Data REST API Routes
Provides endpoints for querying oceanographic sensor data,
buoy readings, species information, and spatial searches.
"""
import sys
import os
import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

logger = logging.getLogger("API-Ocean")
router = APIRouter()


def _get_db_available():
    """Check if database module is available."""
    try:
        from db import queries
        return True
    except ImportError:
        return False


# ── Sample fallback data when DB is not initialized ──────────────────────────

SAMPLE_BUOY_READINGS = [
    {
        "id": i,
        "sensor_id": sid,
        "sensor_name": name,
        "timestamp": 1771600000 + i * 60,
        "lat": lat,
        "lon": lon,
        "sea_surface_temp_c": sst,
        "salinity_psu": sal,
        "chlorophyll_a_mg_m3": chl,
        "dissolved_oxygen_mg_l": do,
        "wave_height_m": wh,
        "anomaly_flag": False,
        "anomaly_reason": None,
    }
    for i, (sid, name, lat, lon, sst, sal, chl, do, wh) in enumerate([
        ("INCOIS-ARB-01", "Arabian Sea Offshore Buoy 1", 15.29, 72.88, 28.5, 36.2, 1.4, 5.8, 1.2),
        ("INCOIS-ARB-02", "Goa Coastal Deep-Water Buoy", 15.49, 73.75, 29.1, 35.8, 2.1, 6.1, 0.9),
        ("INCOIS-BOB-01", "Bay of Bengal Central Buoy", 13.08, 82.27, 29.8, 33.4, 1.8, 5.5, 1.5),
        ("INCOIS-BOB-02", "Visakhapatnam Shelf Buoy", 17.68, 83.51, 29.4, 33.9, 1.6, 5.9, 1.1),
        ("INCOIS-LAK-01", "Lakshadweep Coral Basin Buoy", 10.56, 72.64, 28.9, 35.4, 2.3, 6.3, 0.8),
        ("INCOIS-AND-01", "Andaman Deep Trench Buoy", 11.62, 92.72, 29.6, 32.8, 1.9, 5.2, 1.4),
    ])
]

SAMPLE_SPECIES = [
    {"id": 1, "common_name": "Indian Mackerel", "scientific_name": "Rastrelliger kanagurta", "family": "Scombridae", "habitat_type": "Pelagic", "conservation_status": "Least Concern", "min_sst": 26.0, "max_sst": 30.0, "commercial_value": "High"},
    {"id": 2, "common_name": "Oil Sardine", "scientific_name": "Sardinella longiceps", "family": "Clupeidae", "habitat_type": "Pelagic", "conservation_status": "Least Concern", "min_sst": 27.0, "max_sst": 30.0, "commercial_value": "High"},
    {"id": 3, "common_name": "Hilsa", "scientific_name": "Tenualosa ilisha", "family": "Clupeidae", "habitat_type": "Anadromous", "conservation_status": "Least Concern", "min_sst": 24.0, "max_sst": 30.0, "commercial_value": "Very High"},
    {"id": 4, "common_name": "Bombay Duck", "scientific_name": "Harpadon nehereus", "family": "Synodontidae", "habitat_type": "Demersal", "conservation_status": "Least Concern", "min_sst": 25.0, "max_sst": 29.0, "commercial_value": "Medium"},
    {"id": 5, "common_name": "Yellowfin Tuna", "scientific_name": "Thunnus albacares", "family": "Scombridae", "habitat_type": "Pelagic", "conservation_status": "Near Threatened", "min_sst": 20.0, "max_sst": 31.0, "commercial_value": "Very High"},
    {"id": 6, "common_name": "Penaeid Shrimp", "scientific_name": "Penaeus indicus", "family": "Penaeidae", "habitat_type": "Benthic", "conservation_status": "Least Concern", "min_sst": 25.0, "max_sst": 32.0, "commercial_value": "High"},
]

SAMPLE_GRIDS = [
    {"id": f"GRID-{i:02d}", "name": name, "lat_center": lat, "lon_center": lon}
    for i, (name, lat, lon) in enumerate([
        ("Goa Shelf", 15.4, 73.8), ("Mumbai Offshore", 18.9, 72.8),
        ("Kochi Basin", 9.9, 76.3), ("Visakhapatnam Shelf", 17.7, 83.5),
        ("Lakshadweep Atoll", 10.6, 72.6), ("Andaman Trench", 11.6, 92.7),
        ("Gulf of Mannar", 9.0, 79.0), ("Sundarbans Delta", 21.9, 88.9),
        ("Palk Strait", 9.5, 79.5), ("Karwar Coast", 14.8, 74.1),
    ], start=1)
]


@router.get("/ocean-data/readings")
async def get_buoy_readings(
    sensor_id: Optional[str] = Query(None, description="Filter by specific sensor ID"),
    limit: int = Query(50, ge=1, le=500, description="Number of records to return"),
):
    """Get recent buoy telemetry readings, optionally filtered by sensor."""
    if _get_db_available():
        try:
            from db import queries
            if sensor_id:
                readings = await queries.get_buoy_readings(sensor_id, limit)
            else:
                readings = await queries.get_buoy_readings(None, limit)
            return {"status": "ok", "source": "database", "count": len(readings), "readings": readings}
        except Exception as e:
            logger.warning(f"DB query failed, falling back to sample data: {e}")

    # Fallback to sample data
    data = SAMPLE_BUOY_READINGS
    if sensor_id:
        data = [r for r in data if r["sensor_id"] == sensor_id]
    return {"status": "ok", "source": "sample", "count": len(data[:limit]), "readings": data[:limit]}


@router.get("/ocean-data/grids")
async def get_ocean_grids():
    """Get all ocean grid cells with their metadata."""
    if _get_db_available():
        try:
            from db import queries
            grids = await queries.get_all_grids()
            return {"status": "ok", "source": "database", "count": len(grids), "grids": grids}
        except Exception:
            pass

    return {"status": "ok", "source": "sample", "count": len(SAMPLE_GRIDS), "grids": SAMPLE_GRIDS}


@router.get("/ocean-data/spatial-query")
async def spatial_query(
    lat: float = Query(..., ge=-90, le=90, description="Latitude of center point"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude of center point"),
    radius_km: float = Query(100, ge=1, le=2000, description="Search radius in kilometers"),
):
    """Find buoy readings within a radius of a given coordinate using spatial search."""
    if _get_db_available():
        try:
            from db import queries
            readings = await queries.get_readings_in_area(lat, lon, radius_km, hours=24)
            return {"status": "ok", "source": "database", "center": {"lat": lat, "lon": lon}, "radius_km": radius_km, "count": len(readings), "readings": readings}
        except Exception:
            pass

    # Fallback: simple distance filter on sample data
    import math
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    nearby = [r for r in SAMPLE_BUOY_READINGS if haversine(lat, lon, r["lat"], r["lon"]) <= radius_km]
    return {"status": "ok", "source": "sample", "center": {"lat": lat, "lon": lon}, "radius_km": radius_km, "count": len(nearby), "readings": nearby}


@router.get("/ocean-data/species")
async def get_all_species():
    """Get the catalog of all tracked marine species."""
    if _get_db_available():
        try:
            from db import queries
            species = await queries.get_all_species()
            return {"status": "ok", "source": "database", "count": len(species), "species": species}
        except Exception:
            pass

    return {"status": "ok", "source": "sample", "count": len(SAMPLE_SPECIES), "species": SAMPLE_SPECIES}


@router.get("/ocean-data/species/match")
async def match_species_to_conditions(
    sst: float = Query(..., description="Sea Surface Temperature in °C"),
    salinity: float = Query(35.0, description="Salinity in PSU"),
):
    """Find species whose preferred environmental conditions match the given parameters."""
    matches = []
    for sp in SAMPLE_SPECIES:
        if sp["min_sst"] <= sst <= sp["max_sst"]:
            # Calculate a simple habitat-match confidence
            sst_mid = (sp["min_sst"] + sp["max_sst"]) / 2
            sst_range = (sp["max_sst"] - sp["min_sst"]) / 2
            confidence = max(0, 1 - abs(sst - sst_mid) / sst_range) if sst_range > 0 else 0.5
            matches.append({**sp, "habitat_match_confidence": round(confidence, 3)})

    matches.sort(key=lambda x: x["habitat_match_confidence"], reverse=True)
    return {"status": "ok", "sst": sst, "salinity": salinity, "count": len(matches), "matches": matches}
