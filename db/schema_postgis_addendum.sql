-- =====================================================================
-- schema_postgis_addendum.sql
-- Adds fishing_zones and alerts — present in the original SQLite
-- schema.sql and exported by db/__init__.py (get_fishing_zones,
-- get_active_alerts, insert_alert) but missing from schema_postgis.sql.
-- Run this after schema_postgis.sql.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS fishing_zones (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone_name        TEXT,
    geom             GEOGRAPHY(POINT, 4326) NOT NULL,  -- center point
    radius_km        DOUBLE PRECISION,
    pfz_score        DOUBLE PRECISION,
    dominant_species TEXT,
    valid_from       TIMESTAMPTZ,
    valid_until      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_pfz_validity ON fishing_zones (valid_from, valid_until);
CREATE INDEX IF NOT EXISTS idx_pfz_geom ON fishing_zones USING GIST (geom);

CREATE TABLE IF NOT EXISTS alerts (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type    TEXT NOT NULL,
    severity      TEXT,
    sensor_id     TEXT,
    geom          GEOGRAPHY(POINT, 4326),
    message       TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    acknowledged  BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts (acknowledged, severity);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts (created_at DESC);