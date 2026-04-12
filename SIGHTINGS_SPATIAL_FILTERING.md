# Sightings Feed Spatial Filtering

## Overview

The sightings feed now supports advanced spatial filtering using PostGIS for precise geographic queries. You can filter sightings by ZIP code boundaries or place names with customizable radius.

## API Endpoint

```
POST /v1/socialmedia/api/feed/get/
```

## New Filter Parameters

### 1. ZIP Code Boundary Filtering

Filter sightings that fall **within** the geographic boundary polygon of a ZIP/postal code.

**Parameters:**
- `zipCodeBoundary` (string, required): ZIP or postal code to search
- `zipCodeCountry` (string, optional): Country code (`US` or `CA`). Default: `US`

**Example Request:**
```json
{
  "zipCodeBoundary": "94102",
  "zipCodeCountry": "US"
}
```

**How it works:**
1. Looks up the ZIP code in the `postal_codes` table
2. Retrieves the boundary MultiPolygon geometry
3. Uses PostGIS `ST_Contains()` to find all sightings within the boundary
4. Returns error if ZIP code not found or has no boundary data

**Error Response (404):**
```json
{
  "error": "ZIP/postal code '99999' not found in US or has no boundary data. Try using 'zipCode' parameter for string matching instead."
}
```

**Coverage:**
- **US:** 33,644 ZIP codes with boundaries (81% coverage)
- **CA:** 0 postal codes with boundaries (centroid data only)

### 2. Place Name Filtering

Filter sightings within a specified radius of a named place (city, town, etc.).

**Parameters:**
- `placeName` (string, required): Name of place (e.g., "San Francisco", "Portland")
- `placeCountry` (string, optional): Country code (`US` or `CA`) to narrow search
- `placeRadius` (float, optional): Radius in kilometers. Default: `10`

**Example Request:**
```json
{
  "placeName": "San Francisco",
  "placeCountry": "US",
  "placeRadius": 20
}
```

**How it works:**
1. Looks up place name in the `geonames` table
2. If country specified, searches within that country only
3. Selects most populous matching place
4. Uses PostGIS geographic distance query with the specified radius
5. Returns sightings sorted by distance from place centroid

**Error Response (404):**
```json
{
  "error": "Place name 'Nonexistent City' not found in US. Please check spelling or try a nearby city."
}
```

**Coverage:**
- **US:** 2,241,346 places (cities, towns, landmarks, etc.)
- **CA:** 316,685 places

### 3. Legacy ZIP Code String Match

Original ZIP code filtering (string match on `geocoded_location_zip_code` field).

**Parameters:**
- `zipCode` (string): ZIP code for simple string matching

**Note:** This does NOT use spatial queries and may return sightings from anywhere that have this ZIP in their geocoded location text.

## Combining Filters

Spatial filters can be combined with other existing filters:

**Filter with ZIP boundary + species:**
```json
{
  "zipCodeBoundary": "94102",
  "zipCodeCountry": "US",
  "species": "American Robin"
}
```

**Filter with place name + user:**
```json
{
  "placeName": "Portland",
  "placeCountry": "US",
  "placeRadius": 10,
  "userId": "123e4567-e89b-12d3-a456-426614174000"
}
```

**All available filters:**
- `zipCodeBoundary` + `zipCodeCountry` - Spatial ZIP boundary
- `placeName` + `placeCountry` + `placeRadius` - Place name with radius
- `zipCode` - Legacy string match
- `userLatitude` + `userLongitude` + `distanceRadius` - Custom coordinates with radius
- `species` - Filter by species name
- `userId` - Filter by user UUID
- `userDisplayName` - Filter by user display name (case-insensitive)

## Filter Priority

Filters are applied in this order (first match wins for spatial queries):

1. **ZIP Code Boundary** (`zipCodeBoundary`)
2. **Place Name** (`placeName`)
3. **ZIP Code String** (`zipCode`)
4. **Custom Coordinates** (`userLatitude`, `userLongitude`, `distanceRadius`)
5. **All Posts** (if no spatial filter)

Then the following filters are layered on top:
- Species filter
- User ID filter
- Display name filter

## Response Format

Standard pagination response with sightings sorted by:
- **ZIP Boundary:** Created date (newest first)
- **Place Name:** Distance from place (nearest first)
- **Coordinates:** Distance from coordinates (nearest first)
- **Default:** Created date (newest first)

```json
{
  "count": 181,
  "next": "http://localhost:8000/v1/socialmedia/api/feed/get/?limit=10&offset=10",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "geoprivacy": "public",
      "created_by": "User Name",
      "encounter_datetime": "2026-02-18T16:34:41",
      "species": "Species Name",
      "latitude": 37.7749,
      "longitude": -122.4194,
      ...
    }
  ]
}
```

## Performance

- **ZIP Boundary:** Uses PostGIS spatial index on `true_location_spatial` and `boundary` columns (~50-200ms)
- **Place Name:** Uses PostGIS geography distance with spatial index (~50-200ms)
- **Coordinates:** Uses PostGIS geography distance with spatial index (~50-200ms)

All queries benefit from GIST spatial indexes for efficient large-scale querying.

## Data Requirements

For these features to work, the following data must be imported:

1. **Postal Codes (Centroids):** ✅ Imported (43,147 records)
   - `data/postal_codes/import_postal_codes.sh`

2. **Postal Code Boundaries:** ✅ US imported (33,644 boundaries)
   - `data/postal_codes/import_us_zip_boundaries.sh`

3. **GeoNames Places:** ✅ Imported (2,558,031 records)
   - `data/geonames/import_geonames.sh`

4. **Sightings with Spatial Data:** Requires `true_location_spatial` PointField populated
   - Check: `SELECT COUNT(*) FROM socialmedia_mediapost WHERE true_location_spatial IS NOT NULL;`

## Examples

### Find all bear sightings in San Francisco ZIP 94102
```bash
curl -X POST "http://localhost:8000/v1/socialmedia/api/feed/get/" \
  -H "Content-Type: application/json" \
  -d '{
    "zipCodeBoundary": "94102",
    "zipCodeCountry": "US",
    "species": "Black Bear"
  }'
```

### Find sightings within 5km of Portland, OR
```bash
curl -X POST "http://localhost:8000/v1/socialmedia/api/feed/get/" \
  -H "Content-Type: application/json" \
  -d '{
    "placeName": "Portland",
    "placeCountry": "US",
    "placeRadius": 5
  }'
```

### Find sightings by specific user within city limits
```bash
curl -X POST "http://localhost:8000/v1/socialmedia/api/feed/get/" \
  -H "Content-Type: application/json" \
  -d '{
    "placeName": "Seattle",
    "placeRadius": 15,
    "userDisplayName": "John"
  }'
```
