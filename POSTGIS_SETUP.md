# PostGIS Setup and Testing Guide

## Overview

This project uses GeoDjango with PostGIS for spatial data handling. Three spatial point fields have been added to the `MediaPost` model:
- `public_location_spatial`: For public sightings
- `true_location_spatial`: For obscured sightings (true location kept private)
- `private_location_spatial`: For private sightings

## Requirements

### System Dependencies

For production/staging (PostgreSQL with PostGIS):
```bash
# Install PostGIS and GDAL
sudo apt-get update
sudo apt-get install -y postgresql-{version}-postgis-3 gdal-bin libgdal-dev python3-gdal
```

### Python Dependencies

All required Python packages are already in `requirements.txt`:
- Django 5.0.2
- psycopg2-binary (PostgreSQL adapter)
- GeoDjango is part of Django (contrib.gis)

## Database Setup

### Enable PostGIS Extension

The PostGIS extension is automatically enabled by migration `0012_enable_postgis_extension.py`. 

If you need to enable it manually:
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

### Run Migrations

```bash
python manage.py migrate --settings=config.settings.local
```

This will:
1. Enable the PostGIS extension (migration 0012)
2. Add the three spatial point fields with automatic spatial indexes (migration 0013)

## Populating Existing Data

To populate spatial fields from existing latitude/longitude data:

```bash
# Dry run to see what would be updated
python manage.py populate_spatial_fields --dry-run --settings=config.settings.local

# Actually populate the fields
python manage.py populate_spatial_fields --settings=config.settings.local

# With custom batch size
python manage.py populate_spatial_fields --batch-size=1000 --settings=config.settings.local
```

## Testing

### Running Tests

Tests for spatial functionality are in `siteapps/socialmedia/test_spatial.py`.

**Note:** Spatial tests require Spatialite support which may not be available in all CI environments.
To run tests locally with PostgreSQL+PostGIS:

```bash
# Set up test database with PostGIS
createdb -U your_user wildebackyard_test
psql -U your_user -d wildebackyard_test -c "CREATE EXTENSION postgis;"

# Run tests
python manage.py test siteapps.socialmedia.test_spatial --settings=config.settings.local
```

### Test Coverage

The test suite includes:
- Creation of spatial fields when new sightings are posted
- Verification of correct Point geometry creation
- Verification of SRID (4326 - WGS84)
- Management command functionality
- Dry-run mode testing

## Usage in Code

### Creating Sightings

Spatial fields are automatically populated when creating sightings through the API:

```python
post_data = {
    "postTitle": "Wolf Sighting",
    "privacySetting": "public",
    "latitude": 45.5231,
    "longitude": -122.6765,
    # ... other fields
}
# POST to /v1/socialmedia/posts/create/
# public_location_spatial will be automatically created
```

### Querying Spatial Data

```python
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D  # Distance
from siteapps.socialmedia.models import MediaPost

# Find posts within 10km of a point
point = Point(-122.6765, 45.5231, srid=4326)
nearby_posts = MediaPost.objects.filter(
    public_location_spatial__distance_lte=(point, D(km=10))
)

# Find the closest post
closest = MediaPost.objects.filter(
    public_location_spatial__isnull=False
).distance(point).order_by('distance').first()
```

## Deployment

### GCP App Engine

The PostGIS configuration is already set up for GCP deployments:
- Settings in `config/settings/wildebackyard_api.py` use PostGIS backend
- Cloud SQL PostgreSQL instances support PostGIS extension
- Migrations will automatically run on deployment

### Important Notes

1. **SRID 4326**: All spatial fields use SRID 4326 (WGS84), which is the standard for GPS coordinates
2. **Point Order**: GeoDjango Point uses (longitude, latitude) order, not (latitude, longitude)
3. **Spatial Indexes**: Spatial indexes are automatically created for better query performance
4. **Privacy**: The same security considerations apply to spatial fields as to the float lat/lng fields

## Troubleshooting

### "Could not find the GDAL library"

Install GDAL system library:
```bash
sudo apt-get install -y gdal-bin libgdal-dev
```

### "Unable to load SpatiaLite library"

This occurs in test environments. Use PostgreSQL for testing instead of SQLite:
```bash
python manage.py test --settings=config.settings.local
```

### PostGIS Extension Not Found

Ensure PostGIS is installed in your PostgreSQL instance:
```bash
# On Ubuntu/Debian
sudo apt-get install postgresql-14-postgis-3  # Adjust version as needed

# Verify in PostgreSQL
psql -U your_user -d your_database -c "SELECT PostGIS_version();"
```
