#!/bin/bash
#
# Export IUCN habitat raster tables from local PostgreSQL database
#
# This script exports both iucn_habitat_lvl1 and iucn_habitat_lvl2 tables
# using pg_dump with custom format for efficient compression and restoration.
#
# Output files:
#   - iucn_habitat_lvl1.dump (~2.7GB compressed)
#   - iucn_habitat_lvl2.dump (~2.9GB compressed)
#
# Usage:
#   ./export_habitat_tables.sh

set -e

# Database configuration
DB_NAME="wildebackyard"
DB_USER="jnovak"
DB_HOST="localhost"
DB_PORT="5432"
EXPORT_DIR="/home/jnovak/Projects/WildeBackyardBackend/habitat_exports"

# Create export directory
mkdir -p "$EXPORT_DIR"

echo "============================================================"
echo "IUCN Habitat Table Export"
echo "============================================================"
echo ""
echo "Database: $DB_NAME"
echo "Export directory: $EXPORT_DIR"
echo ""

# Export Level 1 table
echo "Exporting iucn_habitat_lvl1 table..."
PGPASSWORD="Nashorn9450!" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -Fc \
    -t "public.iucn_habitat_lvl1" \
    -f "$EXPORT_DIR/iucn_habitat_lvl1.dump"

echo "✓ Level 1 table exported"
echo ""

# Export Level 2 table
echo "Exporting iucn_habitat_lvl2 table..."
PGPASSWORD="Nashorn9450!" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -Fc \
    -t "public.iucn_habitat_lvl2" \
    -f "$EXPORT_DIR/iucn_habitat_lvl2.dump"

echo "✓ Level 2 table exported"
echo ""

# Get file sizes
echo "Export complete! File sizes:"
ls -lh "$EXPORT_DIR"/*.dump
echo ""

# Calculate total size
TOTAL_SIZE=$(du -sh "$EXPORT_DIR" | cut -f1)
echo "Total export size: $TOTAL_SIZE"
echo ""
echo "============================================================"
echo "Next Steps:"
echo "============================================================"
echo "1. Upload dump files to Google Cloud Storage:"
echo "   gsutil -m cp $EXPORT_DIR/*.dump gs://wildepod-339517-habitat-backup/"
echo ""
echo "2. Run import script on Cloud SQL:"
echo "   ./import_habitat_to_cloudsql.sh"
echo ""
echo "3. Run migration on production:"
echo "   gcloud app deploy app.yaml"
echo "   # Then SSH to instance and run migration"
echo "============================================================"
