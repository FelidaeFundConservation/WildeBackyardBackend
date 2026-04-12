# IUCN Habitat Classification Integration

This module provides API endpoints to query IUCN terrestrial habitat types by geographic coordinates using PostGIS raster data.

## Data Source

Global habitat classification data from:
- **Citation**: Jung, Martin et al. (2020). "A global map of terrestrial habitat types" (Version 003)
- **Source**: [Zenodo DOI: 10.5281/zenodo.3827110](http://doi.org/10.5281/zenodo.3827110)
- **Resolution**: ~100m at equator (0.0009 degrees)
- **Coverage**: Global terrestrial areas
- **SRID**: 4326 (WGS84)

## Database Setup

### Prerequisites
```bash
sudo apt install gdal-bin postgis
```

### Loading Rasters into PostGIS

The TIF rasters must be loaded into PostgreSQL using `raster2pgsql`:

```bash
cd /path/to/iucn_habitatclassification_code_ver003/

# Load Level 1 (broad categories)
raster2pgsql -s 4326 -I -C -M -t 100x100 \
  iucn_habitatclassification_composite_lvl1_ver003.tif \
  public.iucn_habitat_lvl1 | psql -d wildebackyard

# Load Level 2 (detailed categories)
raster2pgsql -s 4326 -I -C -M -t 100x100 \
  iucn_habitatclassification_composite_lvl2_ver003.tif \
  public.iucn_habitat_lvl2 | psql -d wildebackyard
```

**Options explained:**
- `-s 4326`: Set SRID to WGS84
- `-I`: Create spatial index (GIST) on raster
- `-C`: Add raster constraints
- `-M`: Vacuum analyze after import
- `-t 100x100`: Tile raster into 100x100 pixel tiles for better query performance

**Note**: Import may take 30-60 minutes for each raster due to large size (400K x 200K pixels).

### Verify Import

```sql
-- Check table exists and row count
SELECT COUNT(*) FROM iucn_habitat_lvl1;
SELECT COUNT(*) FROM iucn_habitat_lvl2;

-- Check raster metadata
SELECT ST_BandPixelType(rast) AS pixel_type,
       ST_Width(rast) AS width,
       ST_Height(rast) AS height,
       ST_SRID(rast) AS srid
FROM iucn_habitat_lvl1
LIMIT 1;

-- Test query for a known location (San Francisco)
SELECT ST_Value(rast, ST_SetSRID(ST_Point(-122.4194, 37.7749), 4326)) AS habitat_code
FROM iucn_habitat_lvl1
WHERE ST_Intersects(rast, ST_SetSRID(ST_Point(-122.4194, 37.7749), 4326))
LIMIT 1;
```

## API Usage

### Query Habitat by Coordinates

```http
GET /v1/habitat/api/query/?lat=37.7749&lon=-122.4194
```

**Parameters:**
- `lat` (required): Latitude (-90 to 90)
- `lon` (required): Longitude (-180 to 180)

**Response:**
```json
{
  "latitude": 37.7749,
  "longitude": -122.4194,
  "habitatLevel1": {
    "code": 10,
    "name": "Artificial/Terrestrial"
  },
  "habitatLevel2": {
    "code": 145,
    "name": "Habitat code 145"
  }
}
```

**Error Response (out of bounds):**
```json
{
  "error": "Coordinates out of bounds. Lat must be -90 to 90, Lon must be -180 to 180."
}
```

**No Data Response:**
```json
{
  "latitude": 0.0,
  "longitude": 0.0,
  "habitatLevel1": {
    "code": null,
    "name": null
  },
  "habitatLevel2": {
    "code": null,
    "name": null
  },
  "message": "No habitat data available for this location (may be ocean or no data)"
}
```

## Habitat Classification Levels

### Level 1 (Broad Categories)
Based on IUCN habitat classification scheme:
1. Forest
2. Savanna
3. Shrubland
4. Grassland
5. Wetlands
6. Rocky areas
7. Caves and subterranean habitats
8. Desert
9. Marine
10. Artificial/Terrestrial
11. Artificial/Aquatic
12. Introduced vegetation
13. Other

### Level 2 (Detailed Subdivisions)
Level 2 provides finer-grained classifications based on:
- Climate zones (Köppen-Geiger)
- Elevation
- Land cover types
- Management practices (plantations, pastures)
- Wetland types

**TODO**: Complete Level 2 code-to-name mapping based on IUCN scheme.

## Integration with Sighting Reports

The habitat API can enrich wildlife sighting data:

```python
# Example: Add habitat context to MediaPost
from siteapps.habitat.views import HabitatTypeByCoordinateView

# When creating a sighting
lat, lon = 37.7749, -122.4194
# Query habitat (you would call the API or use the view directly)
# Store habitat codes in MediaPost.habitat_type field
```

## Performance Considerations

- **Query time**: ~50-200ms per coordinate (depends on tile cache)
- **Spatial index**: GIST index created on raster for fast queries
- **Tiling**: 100x100 tiles balance query speed vs. storage
- **Caching**: Consider caching common locations (cities, parks)

## Known Limitations

From IUCN dataset documentation:
- Underestimates pastoral land in South Africa, Brazil, East Asia
- Some coastal cells may be unmapped
- Rivers may be missed due to resolution
- Seasonal wetland dynamics may be misclassified

## References

1. Jung, M., Dahal, P.R., Butchart, S.H.M. et al. (2020). A global map of terrestrial habitat types. *Nature Scientific Data*. [DOI: 10.1038/s41597-020-00599-8](https://doi.org/10.1038/s41597-020-00599-8)
2. IUCN Habitat Classification Scheme: https://www.iucnredlist.org/resources/habitat-classification-scheme
3. PostGIS Raster Documentation: https://postgis.net/docs/RT_reference.html
