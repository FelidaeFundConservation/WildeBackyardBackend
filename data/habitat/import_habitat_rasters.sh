#!/bin/bash
# Import IUCN habitat classification rasters into local PostgreSQL database
# This will take 30-60 minutes per raster (large files: 1.9GB + 2.4GB)

set -e  # Exit on any error

RASTER_DIR="/home/jnovak/Projects/iucn_habitatclassification_code_ver003"
DB_NAME="wildebackyard"
DB_USER="jnovak"
DB_HOST="localhost"

echo "=== IUCN Habitat Raster Import ==="
echo ""
echo "This will load ~4GB of raster data into PostgreSQL."
echo "Estimated time: 60-120 minutes total"
echo ""

# Check if raster files exist
if [ ! -f "$RASTER_DIR/iucn_habitatclassification_composite_lvl1_ver003.tif" ]; then
    echo "ERROR: Level 1 raster file not found"
    exit 1
fi

if [ ! -f "$RASTER_DIR/iucn_habitatclassification_composite_lvl2_ver003.tif" ]; then
    echo "ERROR: Level 2 raster file not found"
    exit 1
fi

# Check if tables already exist
echo "Checking if tables already exist..."
if psql -h $DB_HOST -U $DB_USER -d $DB_NAME -tAc "SELECT 1 FROM pg_tables WHERE tablename='iucn_habitat_lvl1'" | grep -q 1; then
    echo "WARNING: Table iucn_habitat_lvl1 already exists!"
    read -p "Drop and recreate? (yes/no): " CONFIRM
    if [ "$CONFIRM" = "yes" ]; then
        echo "Dropping iucn_habitat_lvl1..."
        psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "DROP TABLE IF EXISTS iucn_habitat_lvl1 CASCADE;"
    else
        echo "Skipping Level 1 import."
    fi
else
    CONFIRM="yes"
fi

# Import Level 1 (broad categories - 1.9GB)
if [ "$CONFIRM" = "yes" ]; then
    echo ""
    echo "=== Importing Level 1 (Broad Categories) ==="
    echo "Source: iucn_habitatclassification_composite_lvl1_ver003.tif"
    echo "Size: 1.9GB"
    echo "Started: $(date)"

    cd "$RASTER_DIR"
    raster2pgsql -s 4326 -I -C -M -t 100x100 \
        iucn_habitatclassification_composite_lvl1_ver003.tif \
        public.iucn_habitat_lvl1 | \
        psql -h $DB_HOST -U $DB_USER -d $DB_NAME

    echo "Level 1 import completed: $(date)"

    # Verify
    TILE_COUNT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -tAc "SELECT COUNT(*) FROM iucn_habitat_lvl1")
    echo "Tiles imported: $TILE_COUNT"
fi

# Check Level 2
echo ""
if psql -h $DB_HOST -U $DB_USER -d $DB_NAME -tAc "SELECT 1 FROM pg_tables WHERE tablename='iucn_habitat_lvl2'" | grep -q 1; then
    echo "WARNING: Table iucn_habitat_lvl2 already exists!"
    read -p "Drop and recreate? (yes/no): " CONFIRM2
    if [ "$CONFIRM2" = "yes" ]; then
        echo "Dropping iucn_habitat_lvl2..."
        psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "DROP TABLE IF EXISTS iucn_habitat_lvl2 CASCADE;"
    else
        echo "Skipping Level 2 import."
    fi
else
    CONFIRM2="yes"
fi

# Import Level 2 (detailed categories - 2.4GB)
if [ "$CONFIRM2" = "yes" ]; then
    echo ""
    echo "=== Importing Level 2 (Detailed Categories) ==="
    echo "Source: iucn_habitatclassification_composite_lvl2_ver003.tif"
    echo "Size: 2.4GB"
    echo "Started: $(date)"

    cd "$RASTER_DIR"
    raster2pgsql -s 4326 -I -C -M -t 100x100 \
        iucn_habitatclassification_composite_lvl2_ver003.tif \
        public.iucn_habitat_lvl2 | \
        psql -h $DB_HOST -U $DB_USER -d $DB_NAME

    echo "Level 2 import completed: $(date)"

    # Verify
    TILE_COUNT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -tAc "SELECT COUNT(*) FROM iucn_habitat_lvl2")
    echo "Tiles imported: $TILE_COUNT"
fi

echo ""
echo "=== Import Complete ==="
echo "Finished: $(date)"
echo ""
echo "Test with:"
echo "  curl 'http://localhost:8000/v1/habitat/api/query/?lat=37.7749&lon=-122.4194'"
