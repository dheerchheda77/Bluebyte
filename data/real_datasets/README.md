# BlueByte AI — Real Dataset Sources

This directory contains real open-access marine data fetched from public APIs.

## Files
- `fetch_real_data.py` — Script to fetch/refresh real data from OBIS + NOAA ERDDAP
- `indian_ocean_occurrences.csv` — Merged real fish occurrence + satellite SST data
- `dataset_metadata.json` — Metadata (record counts, sources, fetch timestamp)

## Data Sources

| Source | Agency | License | URL |
|--------|--------|---------|-----|
| Fish Occurrence Records | OBIS (UNESCO) | CC0 Public Domain | https://api.obis.org |
| Sea Surface Temperature | NOAA CoastWatch ERDDAP | US Public Domain | https://coastwatch.pfeg.noaa.gov/erddap |
| Chlorophyll-a (MODIS) | NOAA CoastWatch | US Public Domain | https://coastwatch.pfeg.noaa.gov/erddap |
| Buoy Climatology | INCOIS / World Ocean Atlas 2023 | Open Government Data | https://incois.gov.in/erddap |

## Species Covered
1. Indian Oil Sardine (*Sardinella longiceps*)
2. Indian Mackerel (*Rastrelliger kanagurta*)
3. Yellowfin Tuna (*Thunnus albacares*)
4. Bombay Duck (*Harpadon nehereus*)
5. Penaeid Shrimp (*Penaeus indicus*)
6. Hilsa (*Tenualosa ilisha*)

## How to Refresh Data
```bash
python data/real_datasets/fetch_real_data.py
```

## CSV Column Reference
| Column | Description | Unit |
|--------|-------------|------|
| `species_id` | Internal species code | string |
| `species_name` | Common name | string |
| `scientific` | Scientific name | string |
| `lat` | Latitude of sighting | decimal degrees |
| `lon` | Longitude of sighting | decimal degrees |
| `date` | Date of observation | YYYY-MM-DD |
| `sst_celsius` | Sea Surface Temperature | °C |
| `salinity_psu` | Salinity | Practical Salinity Units |
| `chlorophyll_mg_m3` | Chlorophyll-a | mg/m³ |
| `dissolved_oxygen_mg_l` | Dissolved Oxygen | mg/L |
| `depth_m` | Fishing depth | meters |
| `presence` | Species presence (1=yes) | binary |
| `data_source` | Source APIs used | string |
