-- schema.sql
CREATE TABLE IF NOT EXISTS ocean_grids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grid_code TEXT UNIQUE NOT NULL,
    lat_min REAL NOT NULL,
    lat_max REAL NOT NULL,
    lon_min REAL NOT NULL,
    lon_max REAL NOT NULL,
    area_name TEXT
);

CREATE TABLE IF NOT EXISTS buoy_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    sst REAL,
    salinity REAL,
    chlorophyll_a REAL,
    dissolved_oxygen REAL,
    wave_height REAL,
    current_velocity REAL,
    current_direction REAL,
    anomaly_flag BOOLEAN DEFAULT 0,
    anomaly_reason TEXT,
    z_score_sst REAL,
    z_score_do REAL
);
CREATE INDEX IF NOT EXISTS idx_buoy_sensor_time ON buoy_readings(sensor_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_buoy_spatial ON buoy_readings(lat, lon);
CREATE INDEX IF NOT EXISTS idx_buoy_time ON buoy_readings(timestamp);

CREATE TABLE IF NOT EXISTS species (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    common_name TEXT NOT NULL,
    scientific_name TEXT NOT NULL,
    family TEXT,
    habitat_type TEXT,
    conservation_status TEXT,
    min_sst REAL,
    max_sst REAL,
    min_depth REAL,
    max_depth REAL,
    commercial_value TEXT
);

CREATE TABLE IF NOT EXISTS edna_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id TEXT UNIQUE NOT NULL,
    species_id INTEGER,
    grid_id INTEGER,
    marker_gene TEXT,
    sequence_fragment TEXT,
    detection_confidence REAL,
    collection_date DATETIME,
    FOREIGN KEY(species_id) REFERENCES species(id),
    FOREIGN KEY(grid_id) REFERENCES ocean_grids(id)
);
CREATE INDEX IF NOT EXISTS idx_edna_grid ON edna_samples(grid_id);
CREATE INDEX IF NOT EXISTS idx_edna_species ON edna_samples(species_id);

CREATE TABLE IF NOT EXISTS vessels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id TEXT UNIQUE NOT NULL,
    name TEXT,
    flag TEXT,
    vessel_type TEXT,
    lat REAL,
    lon REAL,
    speed_knots REAL,
    heading_deg REAL,
    last_seen DATETIME
);

CREATE TABLE IF NOT EXISTS fishing_zones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_name TEXT,
    center_lat REAL,
    center_lon REAL,
    radius_km REAL,
    pfz_score REAL,
    dominant_species TEXT,
    valid_from DATETIME,
    valid_until DATETIME
);
CREATE INDEX IF NOT EXISTS idx_pfz_validity ON fishing_zones(valid_from, valid_until);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    severity TEXT,
    sensor_id TEXT,
    lat REAL,
    lon REAL,
    message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    acknowledged BOOLEAN DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(acknowledged, severity);
