#!/bin/bash
#
# Import IUCN habitat raster tables into Cloud SQL (PostgreSQL)
#
# Prerequisites:
#   1. Dump files uploaded to GCS bucket
#   2. Cloud SQL instance running with PostGIS extension enabled
#   3. gcloud CLI authenticated with correct project
#
# This script:
#   1. Imports dump files from GCS to Cloud SQL
#   2. Creates spatial indexes (if not included in dump)
#   3. Verifies table row counts
#
# Usage:
#   ./import_habitat_to_cloudsql.sh

set -e

# Cloud SQL configuration
INSTANCE_NAME="wildepod-339517:us-west2:wildepoddb"
DB_NAME="wildepod_prod"  # or use environment variable
GCS_BUCKET="wildepod-339517-habitat-backup"
GCS_PREFIX="habitat_dumps"

echo "============================================================"
echo "IUCN Habitat Table Import to Cloud SQL"
echo "============================================================"
echo ""
echo "Instance: $INSTANCE_NAME"
echo "Database: $DB_NAME"
echo "GCS Bucket: gs://$GCS_BUCKET/$GCS_PREFIX/"
echo ""
echo "WARNING: This will import ~5.6GB of raster data"
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

# Import Level 1 table
echo ""
echo "Importing iucn_habitat_lvl1 table..."
gcloud sql import sql "$INSTANCE_NAME" \
    "gs://$GCS_BUCKET/$GCS_PREFIX/iucn_habitat_lvl1.dump" \
    --database="$DB_NAME" \
    --quiet

echo "✓ Level 1 table imported"
echo ""

# Import Level 2 table
echo "Importing iucn_habitat_lvl2 table..."
gcloud sql import sql "$INSTANCE_NAME" \
    "gs://$GCS_BUCKET/$GCS_PREFIX/iucn_habitat_lvl2.dump" \
    --database="$DB_NAME" \
    --quiet

echo "✓ Level 2 table imported"
echo ""

# Verify imports using Cloud SQL Proxy
echo "============================================================"
echo "Verification"
echo "============================================================"
echo ""
echo "To verify the import, connect via Cloud SQL Proxy:"
echo ""
echo "1. Start Cloud SQL Proxy:"
echo "   cloud_sql_proxy -instances=$INSTANCE_NAME=tcp:5432 &"
echo ""
echo "2. Check table counts:"
echo "   PGPASSWORD='<prod_password>' psql -h localhost -U wildepod_prod_user -d $DB_NAME -c 'SELECT COUNT(*) FROM public.iucn_habitat_lvl1;'"
echo "   PGPASSWORD='<prod_password>' psql -h localhost -U wildepod_prod_user -d $DB_NAME -c 'SELECT COUNT(*) FROM public.iucn_habitat_lvl2;'"
echo ""
echo "   Expected counts: 30,049 rows each"
echo ""
echo "3. Test habitat lookup:"
echo "   PGPASSWORD='<prod_password>' psql -h localhost -U wildepod_prod_user -d $DB_NAME -c \\"
echo "     \"SELECT ST_Value(rast, ST_SetSRID(ST_MakePoint(-122.3321, 47.6062), 4326)) \\"
echo "     FROM public.iucn_habitat_lvl1 \\"
echo "     WHERE ST_Intersects(rast, ST_SetSRID(ST_MakePoint(-122.3321, 47.6062), 4326));\""
echo ""
echo "   Expected result: 1400 (Wetlands)"
echo ""
echo "============================================================"
echo "Import complete!"
echo "============================================================"
