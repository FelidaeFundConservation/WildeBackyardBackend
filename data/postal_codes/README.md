# Postal Code Database Setup

## Overview

The `postal_codes` table provides geocoding and reverse geocoding for North American postal codes (US ZIP codes and Canadian postal codes).

## Data Structure

### Geometry Columns

The table has **two geometry columns**:

1. **`geom` (POINT)** - Centroid coordinates for each postal code
   - Source: GeoNames postal code database
   - Always populated
   - Use for: Point-based lookups, nearest postal code queries

2. **`boundary` (MULTIPOLYGON)** - Boundary polygon for postal code area
   - Source: Census TIGER/Line (US), Statistics Canada (CA)
   - Optional - NULL until boundary data is imported
   - Use for: Spatial containment queries, map visualization

### Data Fields

```sql
id           SERIAL PRIMARY KEY
country      CHAR(2)                -- US or CA
postal_code  VARCHAR(20)            -- ZIP or postal code
place_name   VARCHAR(180)           -- City/town name
admin1_name  VARCHAR(100)           -- State/province name
admin1_code  VARCHAR(20)            -- State/province code
admin2_name  VARCHAR(100)           -- County/district name
admin2_code  VARCHAR(20)
admin3_name  VARCHAR(100)
admin3_code  VARCHAR(20)
latitude     NUMERIC(10,7)          -- Centroid latitude
longitude    NUMERIC(10,7)          -- Centroid longitude
accuracy     SMALLINT               -- Coordinate accuracy
geom         GEOMETRY(POINT, 4326)  -- Centroid point
boundary     GEOMETRY(MULTIPOLYGON, 4326)  -- Boundary polygon (optional)
```

## Data Import

### Step 1: Centroid Data (GeoNames)

```bash
cd data/postal_codes
./import_postal_codes.sh
```

This imports:
- **41,490** US ZIP codes
- **1,657** Canadian postal codes

### Step 2: Boundary Polygons (Optional)

#### US ZIP Code Boundaries (ZCTA)

Download from Census Bureau TIGER/Line shapefiles:

```bash
cd data/postal_codes
./import_us_zip_boundaries.sh
```

This downloads ~500MB and imports ~33,000 ZIP Code Tabulation Area boundaries.

**Note:** Not all ZIP codes have boundaries (PO Box only, military bases, etc.)

#### Canadian Postal Code Boundaries (FSA)

Canadian boundaries are at FSA (Forward Sortation Area) level - the first 3 characters of a postal code.

1. Download FSA boundaries from Statistics Canada: https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index-eng.cfm
2. Follow instructions in `import_ca_postal_boundaries.sh`

## API Endpoints

### Lookup Postal Code

```http
GET /v1/habitat/api/postalcode/lookup/?code=94102&country=US
```

Returns:
```json
{
  "postalCode": "94102",
  "placeName": "San Francisco",
  "state": "California",
  "stateCode": "CA",
  "county": "City and County of San Francisco",
  "centroid": {
    "latitude": 37.7813,
    "longitude": -122.4167
  },
  "accuracy": 4,
  "country": "US",
  "boundary": {
    "type": "MultiPolygon",
    "coordinates": [[[[...]]]
  }
}
```

**Note:** `boundary` field only present if TIGER/Line data has been imported.

### Search Postal Codes

```http
GET /v1/habitat/api/postalcode/search/?q=San%20Francisco&country=US&limit=10
```

Search by place name or partial postal code.

### Find Nearby Postal Codes

```http
GET /v1/habitat/api/postalcode/nearby/?lat=37.7749&lon=-122.4194&radius=5000&limit=10
```

Find postal codes within radius (meters) of coordinates.

## Use Cases

### Centroid-Based (Current)
- Geocode address to approximate coordinates
- Find nearest postal code to GPS location
- Calculate distance between postal codes
- Display markers on map

### Boundary-Based (After Import)
- Determine which postal code contains a point
- Calculate area of postal code
- Display choropleth maps
- Spatial analysis and statistics
- Accurate boundary visualization

## Performance

- **42,147 records** (41,490 US + 1,657 CA)
- Spatial indexes on both `geom` and `boundary`
- Typical query time: 10-50ms for point lookups
- Boundary queries: 50-200ms depending on complexity

## Data Sources

1. **Centroids:** GeoNames - http://download.geonames.org/export/zip/
2. **US Boundaries:** Census Bureau TIGER/Line ZCTA - https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html
3. **CA Boundaries:** Statistics Canada FSA - https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index-eng.cfm

## Notes

- Some US ZIP codes serve multiple places (duplicates allowed)
- Canadian data is at FSA level (first 3 characters)
- US ZIP+4 codes are normalized to 5-digit ZIP
- Boundary data is ~500MB and optional
