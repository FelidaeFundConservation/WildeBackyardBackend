#!/bin/bash
# Import US ZIP Code Tabulation Area (ZCTA) boundaries from Census TIGER/Line shapefiles
# This adds boundary polygons to the postal_codes table

set -e

DB_NAME="wildebackyard"
DB_USER="${PGUSER:-jnovak}"
YEAR="2023"  # Latest available TIGER/Line year

echo "=== US ZIP Code Boundary Import ==="
echo "This will download ~500MB of data and may take 10-20 minutes"
echo ""

# Download TIGER/Line ZCTA shapefile
TIGER_URL="https://www2.census.gov/geo/tiger/TIGER${YEAR}/ZCTA520/tl_${YEAR}_us_zcta520.zip"
TIGER_FILE="tl_${YEAR}_us_zcta520.zip"

if [ ! -f "$TIGER_FILE" ]; then
    echo "Downloading TIGER/Line ZCTA shapefile..."
    wget -q --show-progress "$TIGER_URL"
else
    echo "TIGER/Line file already downloaded: $TIGER_FILE"
fi

# Extract shapefile
if [ ! -f "tl_${YEAR}_us_zcta520.shp" ]; then
    echo "Extracting shapefile..."
    unzip -o "$TIGER_FILE"
else
    echo "Shapefile already extracted"
fi

# Import shapefile to temporary table using shp2pgsql
echo "Importing shapefile to temporary table..."
shp2pgsql -s 4326 -I -D "tl_${YEAR}_us_zcta520.shp" temp_zcta_boundaries | \
    psql -d "$DB_NAME" -U "$DB_USER" -q

# Update postal_codes table with boundaries
echo "Matching ZIP code boundaries to postal_codes records..."
psql -d "$DB_NAME" -U "$DB_USER" << 'EOF'
-- Update postal_codes with matching ZCTA boundaries
UPDATE postal_codes pc
SET boundary = tb.geom
FROM temp_zcta_boundaries tb
WHERE pc.country = 'US'
  AND pc.postal_code = tb.zcta5ce20;

-- Show statistics
SELECT
    COUNT(*) FILTER (WHERE boundary IS NOT NULL) as with_boundaries,
    COUNT(*) FILTER (WHERE boundary IS NULL) as without_boundaries,
    COUNT(*) as total
FROM postal_codes
WHERE country = 'US';

-- Clean up temporary table
DROP TABLE temp_zcta_boundaries;
EOF

echo ""
echo "US ZIP boundary import complete!"
echo "Note: Some ZIP codes may not have boundaries (PO Box only, military, etc.)"
