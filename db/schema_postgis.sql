-- =====================================================================
-- BlueByte AI — Production Schema
-- PostgreSQL 15+ | PostGIS 3.4+ | TimescaleDB 2.x | H3-PG (optional)
-- Replaces db/schema.sql (SQLite prototype)
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Optional, if the h3-pg extension is installed on the server:
-- CREATE EXTENSION IF NOT EXISTS h3;
-- If h3-pg isn't available, we still store the H3 index as BIGINT,
-- computed application-side with the h3-py library (see etl_pipeline.py).
-- Either path gives you the same indexable column.

-- ---------------------------------------------------------------------
-- 1. OCEAN GRIDS  (kept for backward compatibility with existing zones,
--    but H3 cells are now the primary spatial join key — see buoy_readings)
-- ---------------------------------------------------------------------
CREATE TABLE ocean_grids (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),  -- UUID, not autoincrement:
                                                                  -- stable, portable node id for
                                                                  -- later Neo4j export (see graph_bridge.py)
    grid_code     TEXT UNIQUE NOT NULL,
    area_name     TEXT,
    geom          GEOGRAPHY(POLYGON, 4326) NOT NULL,  -- real polygon, not lat_min/lat_max box
    h3_res5_cells BIGINT[]                              -- precomputed set of H3 res-5 cells
                                                          -- covering this polygon, for fast
                                                          -- grid <-> h3 rollups
);
CREATE INDEX idx_ocean_grids_geom ON ocean_grids USING GIST (geom);

-- ---------------------------------------------------------------------
-- 2. BUOY READINGS — TimescaleDB hypertable
-- ---------------------------------------------------------------------
CREATE TABLE buoy_readings (
    id                  UUID DEFAULT uuid_generate_v4(),
    sensor_id           TEXT NOT NULL,
    ts                  TIMESTAMPTZ NOT NULL,             -- always UTC-anchored
    geom                GEOGRAPHY(POINT, 4326) NOT NULL,  -- real spatial type, GiST-indexable
    h3_index            BIGINT NOT NULL,                  -- H3 cell (res 6, ~3.2km edge) —
                                                            -- O(1) equality joins for grid
                                                            -- aggregation, no bbox math needed
    sst                 DOUBLE PRECISION,
    salinity            DOUBLE PRECISION,
    chlorophyll_a       DOUBLE PRECISION,
    dissolved_oxygen    DOUBLE PRECISION,
    wave_height         DOUBLE PRECISION,
    current_velocity    DOUBLE PRECISION,
    current_direction   DOUBLE PRECISION,
    -- Outlier metadata: ALWAYS populated, NEVER used to drop/clip the raw
    -- sst/salinity/dissolved_oxygen values above. Flags are additive.
    is_outlier          BOOLEAN DEFAULT FALSE,
    outlier_method      TEXT,             -- 'zscore' | 'mad' | 'iqr'
    outlier_fields      TEXT[],           -- which columns triggered it, e.g. {sst,salinity}
    z_score_sst         DOUBLE PRECISION,
    z_score_salinity    DOUBLE PRECISION,
    z_score_do          DOUBLE PRECISION,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_batch_id     UUID,             -- traces every row back to its ETL run
    PRIMARY KEY (sensor_id, ts)           -- natural key: prevents duplicate ingestion
                                            -- of the same sensor+timestamp (fixes bug #4
                                            -- from the review — was previously unenforced)
);

-- Convert to a hypertable, partitioned on time. chunk_time_interval tuned
-- for a moderate-cardinality buoy network (~7 days/chunk keeps chunks
-- small enough for fast pruning without excessive chunk-count overhead).
SELECT create_hypertable('buoy_readings', 'ts', chunk_time_interval => INTERVAL '7 days');

-- Spatial index (GiST) for ST_DWithin / radius queries
CREATE INDEX idx_buoy_geom ON buoy_readings USING GIST (geom);
-- H3 index for grid-cell equality joins (far cheaper than bbox math)
CREATE INDEX idx_buoy_h3 ON buoy_readings (h3_index, ts DESC);
-- Sensor time-series lookups
CREATE INDEX idx_buoy_sensor_ts ON buoy_readings (sensor_id, ts DESC);
-- Outlier queries need to stay fast even though they're a minority of rows
CREATE INDEX idx_buoy_outliers ON buoy_readings (ts DESC) WHERE is_outlier = TRUE;

-- Compress older chunks automatically (columnar compression, ~90%+ size
-- reduction on sensor time-series). Outlier flags are preserved exactly —
-- compression is lossless, it does not alter or drop values.
ALTER TABLE buoy_readings SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'sensor_id, h3_index',
    timescaledb.compress_orderby = 'ts DESC'
);
SELECT add_compression_policy('buoy_readings', INTERVAL '30 days');

-- ---------------------------------------------------------------------
-- 3. CONTINUOUS AGGREGATES — precomputed rollups for fast dashboards.
--    These are separate materialized views; raw buoy_readings rows
--    (including flagged outliers) are never modified or removed.
-- ---------------------------------------------------------------------
CREATE MATERIALIZED VIEW buoy_readings_hourly
WITH (timescaledb.continuous) AS
SELECT
    h3_index,
    sensor_id,
    time_bucket('1 hour', ts) AS bucket,
    avg(sst)              AS avg_sst,
    min(sst)              AS min_sst,
    max(sst)              AS max_sst,      -- min/max deliberately kept alongside
                                             -- avg so a smoothed mean never hides
                                             -- an extreme reading in the same bucket
    stddev(sst)            AS stddev_sst,
    avg(salinity)          AS avg_salinity,
    min(salinity)          AS min_salinity,
    max(salinity)          AS max_salinity,
    stddev(salinity)       AS stddev_salinity,
    avg(dissolved_oxygen)  AS avg_do,
    min(dissolved_oxygen)  AS min_do,
    bool_or(is_outlier)    AS had_outlier,   -- surfaces if ANY reading in this
                                               -- bucket was flagged, so a rollup
                                               -- never quietly absorbs an anomaly
    count(*) FILTER (WHERE is_outlier) AS outlier_count,
    count(*)                AS reading_count
FROM buoy_readings
GROUP BY h3_index, sensor_id, bucket;

SELECT add_continuous_aggregate_policy('buoy_readings_hourly',
    start_offset => INTERVAL '3 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

CREATE MATERIALIZED VIEW buoy_readings_daily
WITH (timescaledb.continuous) AS
SELECT
    h3_index,
    time_bucket('1 day', ts) AS bucket,
    avg(sst) AS avg_sst, min(sst) AS min_sst, max(sst) AS max_sst,
    avg(salinity) AS avg_salinity, min(salinity) AS min_salinity, max(salinity) AS max_salinity,
    bool_or(is_outlier) AS had_outlier,
    count(*) FILTER (WHERE is_outlier) AS outlier_count,
    count(*) AS reading_count
FROM buoy_readings
GROUP BY h3_index, bucket;

SELECT add_continuous_aggregate_policy('buoy_readings_daily',
    start_offset => INTERVAL '90 days',
    end_offset   => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');

-- ---------------------------------------------------------------------
-- 4. RIVER DISCHARGE — separate hypertable (different station network /
--    cadence than ocean buoys, e.g. CWC gauge stations)
-- ---------------------------------------------------------------------
CREATE TABLE river_discharge (
    id               UUID DEFAULT uuid_generate_v4(),
    station_id       TEXT NOT NULL,
    ts               TIMESTAMPTZ NOT NULL,
    geom             GEOGRAPHY(POINT, 4326) NOT NULL,
    h3_index         BIGINT NOT NULL,
    discharge_cumecs DOUBLE PRECISION,       -- cubic meters/sec
    water_level_m    DOUBLE PRECISION,
    is_outlier       BOOLEAN DEFAULT FALSE,   -- flood overflow events land here —
                                                -- NEVER dropped, see etl_pipeline.py
    outlier_method   TEXT,
    z_score_discharge DOUBLE PRECISION,
    ingested_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_batch_id  UUID,
    PRIMARY KEY (station_id, ts)
);
SELECT create_hypertable('river_discharge', 'ts', chunk_time_interval => INTERVAL '7 days');
CREATE INDEX idx_river_geom ON river_discharge USING GIST (geom);
CREATE INDEX idx_river_h3 ON river_discharge (h3_index, ts DESC);

-- ---------------------------------------------------------------------
-- 5. SPECIES / eDNA — UUID keys for graph portability
-- ---------------------------------------------------------------------
CREATE TABLE species (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    common_name         TEXT NOT NULL,
    scientific_name      TEXT NOT NULL,
    family              TEXT,
    habitat_type        TEXT,
    conservation_status  TEXT,
    min_sst             DOUBLE PRECISION,
    max_sst             DOUBLE PRECISION,
    min_salinity        DOUBLE PRECISION,   -- was missing in v1 — needed since
    max_salinity        DOUBLE PRECISION,   -- get_species_for_conditions() silently
                                              -- ignored salinity (bug #2 in review)
    min_depth           DOUBLE PRECISION,
    max_depth           DOUBLE PRECISION,
    commercial_value    TEXT
);

CREATE TABLE edna_samples (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sample_id             TEXT UNIQUE NOT NULL,
    species_id            UUID REFERENCES species(id),
    geom                  GEOGRAPHY(POINT, 4326),
    h3_index              BIGINT,
    marker_gene           TEXT,
    sequence_fragment     TEXT,
    detection_confidence  DOUBLE PRECISION,
    collection_date       TIMESTAMPTZ
);
CREATE INDEX idx_edna_h3 ON edna_samples (h3_index);
CREATE INDEX idx_edna_species ON edna_samples (species_id);
CREATE INDEX idx_edna_geom ON edna_samples USING GIST (geom);

-- ---------------------------------------------------------------------
-- 6. GRAPH BRIDGE TABLE — the PostGIS <-> Neo4j link
--
-- Rather than dual-writing to Postgres and Neo4j at ingest time (fragile,
-- two systems to keep consistent), stage relationships here as they're
-- discovered/computed, then bulk-export on a schedule via neo4j-admin
-- import or LOAD CSV. Every node above already has a UUID, so these
-- edges reference real, portable identifiers — no ID-mapping step needed
-- at export time.
-- ---------------------------------------------------------------------
CREATE TABLE graph_edges (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id       UUID NOT NULL,        -- e.g. species.id, ocean_grids.id, edna_samples.id
    source_label    TEXT NOT NULL,        -- Neo4j node label, e.g. 'Species', 'OceanGrid'
    target_id       UUID NOT NULL,
    target_label    TEXT NOT NULL,
    relation_type   TEXT NOT NULL,        -- e.g. 'DETECTED_IN', 'CO_OCCURS_WITH', 'FEEDS_IN'
    properties      JSONB DEFAULT '{}',   -- edge weight, confidence, time window, etc.
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    computed_by     TEXT                  -- which pipeline/model produced this edge
);
CREATE INDEX idx_graph_edges_source ON graph_edges (source_label, source_id);
CREATE INDEX idx_graph_edges_target ON graph_edges (target_label, target_id);
CREATE INDEX idx_graph_edges_relation ON graph_edges (relation_type);

-- Example edges this supports out of the box:
--   (:Species)-[:DETECTED_IN]->(:OceanGrid)          from edna_samples
--   (:Species)-[:CO_OCCURS_WITH]->(:Species)          computed from co-located eDNA
--   (:OceanGrid)-[:ADJACENT_TO]->(:OceanGrid)          from H3 k-ring neighbors
--   (:BuoyAnomaly)-[:PRECEDED]->(:FishingZoneChange)   from time-lagged correlation