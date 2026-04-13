#!/bin/bash
set -e

# Import only US ZIP boundaries to GCP Cloud SQL
# Assumes geonames and postal_codes tables already exist

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
GCP_PROJECT="wildepod-339517"
GCP_INSTANCE="wildepoddb"
GCP_REGION="us-west2"
GCP_DB="wildebackyard_api_staging"
GCP_USER="wildepod_wildebackyard_api_user"
GCP_PASSWORD="/noABg6yCIUL5IMmueBRyYcqPMwvouxPBPXRbI+P+MU="
PROXY_PORT=5433
PROXY_PID_FILE="/tmp/cloud_sql_proxy_boundaries.pid"
POSTAL_DIR="/home/jnovak/Projects/WildeBackyardBackend/data/postal_codes"

echo -e "${GREEN}=== Import ZIP Boundaries to GCP ===${NC}\n"

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
    > /tmp/cloud_sql_proxy_boundaries.log 2>&1 &
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
        echo "Check logs: tail /tmp/cloud_sql_proxy_boundaries.log"
        kill $PROXY_PID 2>/dev/null || true
        exit 1
    fi
done
echo ""

# Cleanup function to stop proxy on exit
cleanup() {
    echo -e "\n${YELLOW}Stopping Cloud SQL Proxy${NC}"
    if [ -f "$PROXY_PID_FILE" ]; then
        PROXY_PID=$(cat "$PROXY_PID_FILE")
        kill $PROXY_PID 2>/dev/null || true
        rm "$PROXY_PID_FILE"
    fi
    echo -e "${GREEN}✓${NC} Cleanup complete"
}
trap cleanup EXIT

# Step 3: Import US ZIP boundaries
echo -e "${YELLOW}Step 3: Importing US ZIP boundaries (33K polygons)${NC}"
echo "This will take several minutes..."
echo ""

cd "$POSTAL_DIR"

# Download ZIP boundaries if not present
if [ ! -f "tl_2023_us_zcta520.zip" ]; then
    echo "Downloading US ZIP boundaries from Census Bureau..."
    wget -q --show-progress https://www2.census.gov/geo/tiger/TIGER2023/ZCTA520/tl_2023_us_zcta520.zip
fi

# Extract if needed
if [ ! -f "tl_2023_us_zcta520.shp" ]; then
    echo "Extracting shapefile..."
    unzip -o tl_2023_us_zcta520.zip
fi

# Import using shp2pgsql (export PGPASSWORD so it's available in the pipeline)
echo "Importing boundaries to temporary table..."
export PGPASSWORD="$GCP_PASSWORD"
shp2pgsql -s 4326 -D -I tl_2023_us_zcta520.shp temp_zcta | \
    psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" -q

echo ""
echo "Matching boundaries to postal codes..."
psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" << 'EOF'
UPDATE postal_codes pc
SET boundary = zcta.geom
FROM temp_zcta zcta
WHERE pc.country = 'US'
  AND pc.postal_code = zcta.zcta5ce20;

CREATE INDEX IF NOT EXISTS idx_postal_codes_boundary ON postal_codes USING GIST (boundary);

DROP TABLE temp_zcta;

SELECT
    COUNT(*) as total_us_postal_codes,
    COUNT(boundary) as with_boundaries,
    ROUND(100.0 * COUNT(boundary) / COUNT(*), 1) as boundary_coverage_pct
FROM postal_codes
WHERE country = 'US';
EOF

unset PGPASSWORD

echo -e "\n${GREEN}✓${NC} ZIP boundaries import completed"
echo ""

# Step 4: Verify import
echo -e "${YELLOW}Step 4: Verifying import${NC}"
export PGPASSWORD="$GCP_PASSWORD"
psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" << 'EOF'
SELECT
    'postal_codes' as table_name,
    COUNT(*) as total_rows,
    COUNT(boundary) as with_boundaries,
    pg_size_pretty(pg_total_relation_size('postal_codes')) as total_size
FROM postal_codes;
EOF
unset PGPASSWORD

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}ZIP boundaries import completed successfully!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "The postal_codes table now has ZIP boundary polygons in GCP"
echo ""
