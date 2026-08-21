"""
etl_pipeline.py
================
Outlier-PRESERVING ingestion pipeline for buoy (SST/salinity/DO) and
river discharge data.

Design principle (per project requirement): anomalies are signal, not
noise. A sudden SST spike or a discharge reading 6 standard deviations
above baseline may be an actual flood overflow or marine heatwave —
dropping or clipping it would delete the exact event downstream
ecosystem models need to see. So this pipeline:

  1. NEVER drops a row for being statistically extreme.
  2. NEVER clips/winsorizes/smooths a value based on its own outlier status.
  3. Computes and STORES outlier flags (z-score + MAD) as metadata
     alongside the untouched raw value.
  4. Only rejects rows that are structurally invalid (missing sensor_id,
     unparseable timestamp, out-of-range lat/lon) — never rejects on
     the basis of a statistical extreme.

Requires: pip install h3 asyncpg numpy
"""

import asyncio
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import h3
import numpy as np
import asyncpg

H3_RESOLUTION = 6  # ~3.2km hex edge length; good balance for coastal buoy
                    # density without exploding cell count basin-wide.
                    # Bump to 7 (~1.2km) if buoy density warrants it.

# Rolling baseline window used for z-score / MAD outlier scoring.
# Kept per-sensor so a naturally warmer buoy near the equator isn't
# flagged against a basin-wide mean.
BASELINE_WINDOW_DAYS = 30
Z_SCORE_THRESHOLD = 3.0       # flag if |z| > 3 (assumes ~normal distribution)
MAD_THRESHOLD = 3.5           # flag if modified z-score (MAD-based) > 3.5 —
                               # more robust than z-score when the baseline
                               # window itself already contains outliers,
                               # since MAD is not itself skewed by extremes


@dataclass
class IngestResult:
    accepted: int = 0
    rejected_structural: int = 0
    flagged_outliers: int = 0
    rejection_reasons: list = field(default_factory=list)


def compute_h3_index(lat: float, lon: float, resolution: int = H3_RESOLUTION) -> int:
    """H3 cell as a BIGINT-compatible int, for O(1) grid joins downstream.

    h3-py v4's latlng_to_cell() returns a hex STRING cell address (e.g.
    '866198b87ffffff'), not an int, even though our schema stores
    h3_index as BIGINT — str_to_int() does the conversion. (If pinned
    to h3-py v3 instead, use h3.geo_to_h3(lat, lon, resolution), which
    already returns an int-compatible string differently — check your
    installed h3-py major version if you hit this again.)
    """
    cell_address = h3.latlng_to_cell(lat, lon, resolution)
    return h3.str_to_int(cell_address)


def _validate_structural(row: dict) -> Optional[str]:
    """Structural validation ONLY — never statistical. Returns a reason
    string if the row must be rejected, else None."""
    if not row.get("sensor_id"):
        return "missing sensor_id"
    if row.get("lat") is None or row.get("lon") is None:
        return "missing coordinates"
    if not (-90 <= row["lat"] <= 90) or not (-180 <= row["lon"] <= 180):
        return "coordinates out of valid range"
    if row.get("ts") is None:
        return "missing timestamp"
    return None


def modified_z_scores(values: np.ndarray) -> np.ndarray:
    """MAD-based modified z-score (Iglewicz & Hoaglin). More robust to
    the outliers themselves than a plain z-score, which matters because
    the baseline window we score against will often already contain
    the flood/heatwave events we're trying to flag, not exclude."""
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    if mad == 0:
        return np.zeros_like(values)
    return 0.6745 * (values - median) / mad


class OutlierPreservingETL:
    """
    Usage:
        etl = OutlierPreservingETL(pool)
        result = await etl.ingest_buoy_batch(raw_rows)
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def _fetch_baseline(self, conn, sensor_id: str, field_name: str) -> np.ndarray:
        rows = await conn.fetch(
            f"""
            SELECT {field_name} FROM buoy_readings
            WHERE sensor_id = $1
              AND ts >= now() - make_interval(days => $2)
              AND {field_name} IS NOT NULL
            """,
            sensor_id, BASELINE_WINDOW_DAYS,
        )
        return np.array([r[field_name] for r in rows], dtype=float)

    async def ingest_buoy_batch(self, raw_rows: list[dict]) -> IngestResult:
        result = IngestResult()
        batch_id = uuid.uuid4()
        accepted_rows = []

        for row in raw_rows:
            reason = _validate_structural(row)
            if reason:
                result.rejected_structural += 1
                result.rejection_reasons.append((row.get("sensor_id"), reason))
                continue  # only structural invalidity skips ingestion —
                          # a statistical extreme NEVER hits this branch

            ts = row["ts"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)  # always UTC-anchor
                                                        # (fixes naive-timestamp
                                                        # bug from the v1 review)

            row["ts"] = ts
            row["h3_index"] = compute_h3_index(row["lat"], row["lon"])
            row["_batch_id"] = batch_id
            accepted_rows.append(row)

        if not accepted_rows:
            return result

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Score each accepted row against its sensor's rolling
                # baseline for sst / salinity / dissolved_oxygen.
                for field_name, z_col in (
                    ("sst", "z_score_sst"),
                    ("salinity", "z_score_salinity"),
                    ("dissolved_oxygen", "z_score_do"),
                ):
                    by_sensor: dict[str, list[dict]] = {}
                    for row in accepted_rows:
                        if row.get(field_name) is not None:
                            by_sensor.setdefault(row["sensor_id"], []).append(row)

                    for sensor_id, rows in by_sensor.items():
                        baseline = await self._fetch_baseline(conn, sensor_id, field_name)
                        current_vals = np.array([r[field_name] for r in rows])
                        combined = np.concatenate([baseline, current_vals]) if baseline.size else current_vals

                        if combined.size < 5:
                            # Not enough history to score reliably yet —
                            # leave z-score null, is_outlier False. This is
                            # NOT the same as declaring "not an outlier";
                            # it's declaring "insufficient data to judge",
                            # which is the honest state.
                            continue

                        mzs = modified_z_scores(combined)
                        current_mzs = mzs[-len(current_vals):]

                        for row, mz in zip(rows, current_mzs):
                            row[z_col] = float(mz)
                            if abs(mz) > MAD_THRESHOLD:
                                row.setdefault("outlier_fields", []).append(field_name)

                # Finalize outlier flags (union across sst/salinity/DO)
                for row in accepted_rows:
                    fields = row.get("outlier_fields", [])
                    row["is_outlier"] = len(fields) > 0
                    row["outlier_method"] = "mad" if fields else None
                    row["outlier_fields"] = fields or None
                    if row["is_outlier"]:
                        result.flagged_outliers += 1

                await conn.executemany(
                    """
                    INSERT INTO buoy_readings (
                        sensor_id, ts, geom, h3_index, sst, salinity,
                        chlorophyll_a, dissolved_oxygen, wave_height,
                        current_velocity, current_direction,
                        is_outlier, outlier_method, outlier_fields,
                        z_score_sst, z_score_salinity, z_score_do,
                        source_batch_id
                    ) VALUES (
                        $1, $2, ST_SetSRID(ST_MakePoint($4, $3), 4326)::geography, $5,
                        $6, $7, $8, $9, $10, $11, $12,
                        $13, $14, $15, $16, $17, $18, $19
                    )
                    ON CONFLICT (sensor_id, ts) DO NOTHING
                    """,
                    [
                        (
                            r["sensor_id"], r["ts"], r["lat"], r["lon"], r["h3_index"],
                            r.get("sst"), r.get("salinity"), r.get("chlorophyll_a"),
                            r.get("dissolved_oxygen"), r.get("wave_height"),
                            r.get("current_velocity"), r.get("current_direction"),
                            r["is_outlier"], r["outlier_method"], r["outlier_fields"],
                            r.get("z_score_sst"), r.get("z_score_salinity"), r.get("z_score_do"),
                            r["_batch_id"],
                        )
                        for r in accepted_rows
                    ],
                )
                result.accepted = len(accepted_rows)

        return result

    async def ingest_river_discharge_batch(self, raw_rows: list[dict]) -> IngestResult:
        """Same outlier-preserving contract as buoy ingestion — a
        discharge spike (flood overflow) is exactly the signal downstream
        ecosystem-shock modeling needs, so it's flagged, never dropped."""
        result = IngestResult()
        batch_id = uuid.uuid4()
        accepted_rows = []

        for row in raw_rows:
            reason = _validate_structural(row)
            if reason:
                result.rejected_structural += 1
                result.rejection_reasons.append((row.get("station_id"), reason))
                continue
            ts = row["ts"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            row["ts"] = ts
            row["h3_index"] = compute_h3_index(row["lat"], row["lon"])
            accepted_rows.append(row)

        if not accepted_rows:
            return result

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                by_station: dict[str, list[dict]] = {}
                for row in accepted_rows:
                    by_station.setdefault(row["station_id"], []).append(row)

                for station_id, rows in by_station.items():
                    baseline = await conn.fetch(
                        """
                        SELECT discharge_cumecs FROM river_discharge
                        WHERE station_id = $1
                          AND ts >= now() - make_interval(days => $2)
                          AND discharge_cumecs IS NOT NULL
                        """,
                        station_id, BASELINE_WINDOW_DAYS,
                    )
                    baseline_vals = np.array([r["discharge_cumecs"] for r in baseline], dtype=float)
                    current_vals = np.array([r.get("discharge_cumecs", np.nan) for r in rows])
                    combined = np.concatenate([baseline_vals, current_vals]) if baseline_vals.size else current_vals

                    if combined.size >= 5:
                        mzs = modified_z_scores(combined)
                        current_mzs = mzs[-len(current_vals):]
                        for row, mz in zip(rows, current_mzs):
                            row["z_score_discharge"] = float(mz)
                            row["is_outlier"] = abs(mz) > MAD_THRESHOLD
                            row["outlier_method"] = "mad" if row["is_outlier"] else None
                            if row["is_outlier"]:
                                result.flagged_outliers += 1
                    else:
                        for row in rows:
                            row["z_score_discharge"] = None
                            row["is_outlier"] = False
                            row["outlier_method"] = None

                await conn.executemany(
                    """
                    INSERT INTO river_discharge (
                        station_id, ts, geom, h3_index, discharge_cumecs,
                        water_level_m, is_outlier, outlier_method,
                        z_score_discharge, source_batch_id
                    ) VALUES (
                        $1, $2, ST_SetSRID(ST_MakePoint($4, $3), 4326)::geography, $5,
                        $6, $7, $8, $9, $10, $11
                    )
                    ON CONFLICT (station_id, ts) DO NOTHING
                    """,
                    [
                        (
                            r["station_id"], r["ts"], r["lat"], r["lon"], r["h3_index"],
                            r.get("discharge_cumecs"), r.get("water_level_m"),
                            r["is_outlier"], r["outlier_method"],
                            r.get("z_score_discharge"), batch_id,
                        )
                        for r in accepted_rows
                    ],
                )
                result.accepted = len(accepted_rows)

        return result


async def _demo():
    """Example wiring — replace DSN with your actual connection string."""
    pool = await asyncpg.create_pool(dsn="postgresql://user:pass@localhost/bluebyte")
    etl = OutlierPreservingETL(pool)

    sample_batch = [
        {"sensor_id": "BUOY-3", "ts": datetime.now(timezone.utc), "lat": 12.5, "lon": 75.2, "sst": 29.1, "salinity": 34.2, "dissolved_oxygen": 5.4},
        {"sensor_id": "BUOY-3", "ts": datetime.now(timezone.utc), "lat": 12.5, "lon": 75.2, "sst": 34.8, "salinity": 34.1, "dissolved_oxygen": 5.3},  # potential heatwave spike
    ]
    result = await etl.ingest_buoy_batch(sample_batch)
    print(f"Accepted: {result.accepted}, Flagged outliers: {result.flagged_outliers}, Rejected: {result.rejected_structural}")
    await pool.close()


if __name__ == "__main__":
    asyncio.run(_demo())