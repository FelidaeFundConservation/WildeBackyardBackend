#!/bin/bash
set -e

# Migration script to copy geospatial tables from local to GCP Cloud SQL
# Tables: geonames, postal_codes, admin1_codes, feature_codes

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
LOCAL_DB="wildebackyard"
LOCAL_USER="jnovak"
GCP_PROJECT="wildepod-339517"
GCP_INSTANCE="wildepoddb"
GCP_REGION="us-west2"
GCP_DB="wildebackyard_api_staging"
GCP_USER="wildepod_wildebackyard_api_user"
EXPORT_DIR="/tmp/gcp_migration_$(date +%Y%m%d_%H%M%S)"

# Tables to migrate
TABLES=("admin1_codes" "feature_codes" "geonames" "postal_codes")

echo -e "${GREEN}=== GCP Geospatial Data Migration ===${NC}\n"

# Step 1: Create export directory
echo -e "${YELLOW}Step 1: Creating export directory${NC}"
mkdir -p "$EXPORT_DIR"
echo "Export directory: $EXPORT_DIR"
echo ""

# Step 2: Export table schemas and data from local database
echo -e "${YELLOW}Step 2: Exporting tables from local database${NC}"
for table in "${TABLES[@]}"; do
    echo "Exporting $table..."

    # Get row count
    row_count=$(psql -d "$LOCAL_DB" -t -c "SELECT COUNT(*) FROM $table;" | xargs)
    echo "  Rows: $row_count"

    # Export schema only (CREATE TABLE statements)
    pg_dump -d "$LOCAL_DB" -U "$LOCAL_USER" \
        --schema-only \
        --table="$table" \
        --no-owner \
        --no-acl \
        > "$EXPORT_DIR/${table}_schema.sql"

    # Export data only (COPY statements for faster import)
    pg_dump -d "$LOCAL_DB" -U "$LOCAL_USER" \
        --data-only \
        --table="$table" \
        --no-owner \
        --no-acl \
        > "$EXPORT_DIR/${table}_data.sql"

    # Get file sizes
    schema_size=$(du -h "$EXPORT_DIR/${table}_schema.sql" | cut -f1)
    data_size=$(du -h "$EXPORT_DIR/${table}_data.sql" | cut -f1)
    echo -e "  ${GREEN}✓${NC} Schema: $schema_size, Data: $data_size"
done
echo ""

# Step 3: Create combined import scripts
echo -e "${YELLOW}Step 3: Creating combined import script${NC}"

cat > "$EXPORT_DIR/import_all.sql" <<'EOF'
-- Combined import script for all geospatial tables
-- Run this using Cloud SQL Proxy or gcloud sql connect

-- Enable PostGIS extension if not already enabled
CREATE EXTENSION IF NOT EXISTS postgis;

\echo 'Creating admin1_codes table...'
\i admin1_codes_schema.sql
\echo 'Importing admin1_codes data...'
\i admin1_codes_data.sql

\echo 'Creating feature_codes table...'
\i feature_codes_schema.sql
\echo 'Importing feature_codes data...'
\i feature_codes_data.sql

\echo 'Creating geonames table...'
\i geonames_schema.sql
\echo 'Importing geonames data...'
\i geonames_data.sql

\echo 'Creating postal_codes table...'
\i postal_codes_schema.sql
\echo 'Importing postal_codes data...'
\i postal_codes_data.sql

\echo 'Verifying record counts...'
SELECT 'admin1_codes' as table_name, COUNT(*) as row_count FROM admin1_codes
UNION ALL
SELECT 'feature_codes', COUNT(*) FROM feature_codes
UNION ALL
SELECT 'geonames', COUNT(*) FROM geonames
UNION ALL
SELECT 'postal_codes', COUNT(*) FROM postal_codes;

\echo 'Migration complete!'
EOF

echo -e "${GREEN}✓${NC} Created import_all.sql"
echo ""

# Create summary
echo -e "${YELLOW}Step 4: Export Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Export completed successfully!"
echo ""
echo "Location: $EXPORT_DIR"
echo ""
echo "Files created:"
for table in "${TABLES[@]}"; do
    schema_size=$(du -h "$EXPORT_DIR/${table}_schema.sql" | cut -f1)
    data_size=$(du -h "$EXPORT_DIR/${table}_data.sql" | cut -f1)
    row_count=$(psql -d "$LOCAL_DB" -t -c "SELECT COUNT(*) FROM $table;" | xargs)
    printf "  %-20s Schema: %8s  Data: %8s  Rows: %10s\n" "$table" "$schema_size" "$data_size" "$row_count"
done
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 5: Provide import instructions
echo -e "${YELLOW}Step 5: Import to GCP Cloud SQL${NC}"
echo ""
echo "Choose ONE of these methods to import to GCP:"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}METHOD 1: Using Cloud SQL Proxy (RECOMMENDED)${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# 1. Authenticate with GCP"
echo "gcloud auth login"
echo "gcloud config set project $GCP_PROJECT"
echo ""
echo "# 2. Start Cloud SQL Proxy in a separate terminal"
echo "cloud_sql_proxy -instances=${GCP_PROJECT}:${GCP_REGION}:${GCP_INSTANCE}=tcp:5433"
echo ""
echo "# 3. Import the data (in this terminal)"
echo "cd $EXPORT_DIR"
echo "PGPASSWORD='<password>' psql -h localhost -p 5433 -U $GCP_USER -d $GCP_DB -f import_all.sql"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}METHOD 2: Using gcloud sql connect${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# 1. Authenticate with GCP"
echo "gcloud auth login"
echo "gcloud config set project $GCP_PROJECT"
echo ""
echo "# 2. Connect and import"
echo "gcloud sql connect $GCP_INSTANCE --user=$GCP_USER --database=$GCP_DB"
echo ""
echo "# Once connected to PostgreSQL:"
echo "\\cd $EXPORT_DIR"
echo "\\i import_all.sql"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}METHOD 3: Manual table-by-table import${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "For each table, run:"
echo "PGPASSWORD='<password>' psql -h localhost -p 5433 -U $GCP_USER -d $GCP_DB \\"
echo "  -f ${EXPORT_DIR}/<table>_schema.sql"
echo "PGPASSWORD='<password>' psql -h localhost -p 5433 -U $GCP_USER -d $GCP_DB \\"
echo "  -f ${EXPORT_DIR}/<table>_data.sql"
echo ""
echo "Tables:"
for table in "${TABLES[@]}"; do
    echo "  - $table"
done
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${YELLOW}IMPORTANT NOTES:${NC}"
echo "1. Ensure PostGIS extension is installed on GCP Cloud SQL instance"
echo "2. The password for $GCP_USER is URL-encoded in app.yaml"
echo "3. Decoded password: /noABg6yCIUL5IMmueBRyYcqPMwvouxPBPXRbI+P+MU="
echo "4. Large tables (geonames: 2.5M rows) may take several minutes to import"
echo "5. Verify import with: SELECT COUNT(*) FROM <table_name>;"
echo ""
echo -e "${GREEN}Export files are ready in: $EXPORT_DIR${NC}"
echo ""
