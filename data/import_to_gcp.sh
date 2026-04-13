#!/bin/bash
set -e

# Automated import script for GCP Cloud SQL
# This script will start Cloud SQL Proxy, import the data, and clean up

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
EXPORT_DIR="/tmp/gcp_migration_20260412_095041"
GCP_PROJECT="wildepod-339517"
GCP_INSTANCE="wildepoddb"
GCP_REGION="us-west2"
GCP_DB="wildebackyard_api_staging"
GCP_USER="wildepod_wildebackyard_api_user"
# Decoded password from app.yaml
GCP_PASSWORD="/REDACTED="
PROXY_PORT=5433
PROXY_PID_FILE="/tmp/cloud_sql_proxy.pid"

echo -e "${GREEN}=== Automated GCP Cloud SQL Import ===${NC}\n"

# Check if export directory exists
if [ ! -d "$EXPORT_DIR" ]; then
    echo -e "${RED}Error: Export directory not found: $EXPORT_DIR${NC}"
    echo "Please run ./data/migrate_to_gcp.sh first to export the data"
    exit 1
fi

# Check if import_all.sql exists
if [ ! -f "$EXPORT_DIR/import_all.sql" ]; then
    echo -e "${RED}Error: import_all.sql not found in $EXPORT_DIR${NC}"
    exit 1
fi

# Step 1: Set GCP project
echo -e "${YELLOW}Step 1: Setting GCP project${NC}"
gcloud config set project "$GCP_PROJECT" --quiet
echo -e "${GREEN}✓${NC} Project set to $GCP_PROJECT"
echo ""

# Step 2: Start Cloud SQL Proxy
echo -e "${YELLOW}Step 2: Starting Cloud SQL Proxy${NC}"
echo "Instance: ${GCP_PROJECT}:${GCP_REGION}:${GCP_INSTANCE}"
echo "Port: $PROXY_PORT"

# Kill any existing proxy on this port
if lsof -Pi :$PROXY_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "Killing existing process on port $PROXY_PORT..."
    kill $(lsof -Pi :$PROXY_PORT -sTCP:LISTEN -t) 2>/dev/null || true
    sleep 2
fi

# Start Cloud SQL Proxy in background
cloud_sql_proxy -instances="${GCP_PROJECT}:${GCP_REGION}:${GCP_INSTANCE}=tcp:${PROXY_PORT}" \
    > /tmp/cloud_sql_proxy.log 2>&1 &
PROXY_PID=$!
echo $PROXY_PID > "$PROXY_PID_FILE"
echo "Cloud SQL Proxy PID: $PROXY_PID"

# Wait for proxy to be ready
echo -n "Waiting for Cloud SQL Proxy to be ready"
for i in {1..30}; do
    if pg_isready -h localhost -p $PROXY_PORT > /dev/null 2>&1; then
        echo -e "\n${GREEN}✓${NC} Cloud SQL Proxy is ready"
        break
    fi
    echo -n "."
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "\n${RED}Error: Cloud SQL Proxy failed to start${NC}"
        echo "Check logs: tail /tmp/cloud_sql_proxy.log"
        kill $PROXY_PID 2>/dev/null || true
        exit 1
    fi
done
echo ""

# Step 3: Verify PostGIS extension
echo -e "${YELLOW}Step 3: Verifying PostGIS extension${NC}"
PGPASSWORD="$GCP_PASSWORD" psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -c "CREATE EXTENSION IF NOT EXISTS postgis;" \
    -c "SELECT PostGIS_version();" -t | head -1 | xargs
echo -e "${GREEN}✓${NC} PostGIS extension verified"
echo ""

# Step 4: Import data
echo -e "${YELLOW}Step 4: Importing geospatial tables${NC}"
echo "This may take several minutes for large tables..."
echo ""

cd "$EXPORT_DIR"

# Import with progress
PGPASSWORD="$GCP_PASSWORD" psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -f import_all.sql

echo ""
echo -e "${GREEN}✓${NC} Data import completed"
echo ""

# Step 5: Verify import
echo -e "${YELLOW}Step 5: Verifying import${NC}"
echo "Table counts:"
PGPASSWORD="$GCP_PASSWORD" psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -c "SELECT
        'admin1_codes' as table_name,
        COUNT(*) as row_count,
        pg_size_pretty(pg_total_relation_size('admin1_codes')) as size
    FROM admin1_codes
    UNION ALL
    SELECT 'feature_codes', COUNT(*), pg_size_pretty(pg_total_relation_size('feature_codes'))
    FROM feature_codes
    UNION ALL
    SELECT 'geonames', COUNT(*), pg_size_pretty(pg_total_relation_size('geonames'))
    FROM geonames
    UNION ALL
    SELECT 'postal_codes', COUNT(*), pg_size_pretty(pg_total_relation_size('postal_codes'))
    FROM postal_codes
    ORDER BY row_count DESC;"

echo ""

# Step 6: Verify spatial indexes
echo -e "${YELLOW}Step 6: Verifying spatial indexes${NC}"
PGPASSWORD="$GCP_PASSWORD" psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -c "SELECT
        schemaname,
        tablename,
        indexname,
        indexdef
    FROM pg_indexes
    WHERE tablename IN ('geonames', 'postal_codes')
    AND indexname LIKE '%geom%'
    ORDER BY tablename, indexname;" -t | grep -v "^$" | head -10

echo -e "${GREEN}✓${NC} Spatial indexes verified"
echo ""

# Step 7: Stop Cloud SQL Proxy
echo -e "${YELLOW}Step 7: Stopping Cloud SQL Proxy${NC}"
if [ -f "$PROXY_PID_FILE" ]; then
    PROXY_PID=$(cat "$PROXY_PID_FILE")
    kill $PROXY_PID 2>/dev/null || true
    rm "$PROXY_PID_FILE"
    echo -e "${GREEN}✓${NC} Cloud SQL Proxy stopped"
else
    kill $PROXY_PID 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Cloud SQL Proxy stopped"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}Migration completed successfully!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "1. Test the API endpoints on GCP"
echo "2. Run Django migrations for habitat app:"
echo "   gcloud app deploy app.yaml --quiet"
echo "   (or use ./scripts/deploy_gcp.sh --config app.yaml --promote)"
echo ""
echo "3. Verify API endpoints work:"
echo "   curl https://wildebackyard-api-dot-wildepod-339517.uc.r.appspot.com/v1/habitat/api/geonames/search/?name=Seattle&country=US"
echo ""
echo -e "${YELLOW}Note: Remember to run Django migrations if habitat app changes are deployed${NC}"
echo ""
