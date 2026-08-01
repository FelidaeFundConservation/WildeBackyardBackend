#!/bin/bash
set -e

# Direct import script - runs original import scripts against GCP Cloud SQL
# Avoids pg_dump compatibility issues with transaction_timeout

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
PROXY_PID_FILE="/tmp/cloud_sql_proxy_direct.pid"

# Directories
GEONAMES_DIR="/home/jnovak/Projects/WildeBackyardBackend/data/geonames"
POSTAL_DIR="/home/jnovak/Projects/WildeBackyardBackend/data/postal_codes"

echo -e "${GREEN}=== Direct Import to GCP Cloud SQL ===${NC}\n"

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
    > /tmp/cloud_sql_proxy_direct.log 2>&1 &
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
        echo "Check logs: tail /tmp/cloud_sql_proxy_direct.log"
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

# Step 3: Verify PostGIS extension
echo -e "${YELLOW}Step 3: Verifying PostGIS extension${NC}"
export PGPASSWORD="$GCP_PASSWORD"
psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -c "CREATE EXTENSION IF NOT EXISTS postgis;" \
    -c "SELECT PostGIS_version();" -t 2>&1 | grep -v "NOTICE" | head -1 | xargs
echo -e "${GREEN}✓${NC} PostGIS extension verified"
unset PGPASSWORD
echo ""

# Step 4: Creating GeoNames schema
echo -e "${YELLOW}Step 4: Creating GeoNames schema${NC}"
export PGPASSWORD="$GCP_PASSWORD"
psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -f "$GEONAMES_DIR/create_geonames_schema.sql" 2>&1 | grep -v "NOTICE"
echo -e "${GREEN}✓${NC} GeoNames schema created"
unset PGPASSWORD
echo ""

# Step 5: Import GeoNames data
echo -e "${YELLOW}Step 5: Importing GeoNames data (2.5M rows)${NC}"
echo "This will take several minutes..."
echo ""

cd "$GEONAMES_DIR"

# Check if data files exist
if [ ! -f "allCountries_US.txt" ] || [ ! -f "allCountries_CA.txt" ]; then
    echo -e "${YELLOW}Data files not found. Extracting from ZIP files...${NC}"
    [ -f "US.zip" ] && unzip -o US.zip
    [ -f "CA.zip" ] && unzip -o CA.zip
    # Rename to expected format
    [ -f "US.txt" ] && mv US.txt allCountries_US.txt
    [ -f "CA.txt" ] && mv CA.txt allCountries_CA.txt
fi

# Import US data (specify columns to exclude generated geom column)
echo "Importing US places..."
export PGPASSWORD="$GCP_PASSWORD"
psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -c "\COPY geonames (geonameid, name, asciiname, alternatenames, latitude, longitude, fclass, fcode, country, cc2, admin1, admin2, admin3, admin4, population, elevation, gtopo30, timezone, moddate) FROM 'allCountries_US.txt' WITH (FORMAT csv, DELIMITER E'\t', NULL '', QUOTE E'\b');"

echo "Importing Canada places..."
psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -c "\COPY geonames (geonameid, name, asciiname, alternatenames, latitude, longitude, fclass, fcode, country, cc2, admin1, admin2, admin3, admin4, population, elevation, gtopo30, timezone, moddate) FROM 'allCountries_CA.txt' WITH (FORMAT csv, DELIMITER E'\t', NULL '', QUOTE E'\b');"

# Import admin1 codes
echo "Importing admin1 codes..."
psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -c "\COPY admin1_codes FROM 'admin1CodesASCII.txt' WITH (FORMAT csv, DELIMITER E'\t');"

# Import feature codes
echo "Importing feature codes..."
psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -c "\COPY feature_codes FROM 'featureCodes_en.txt' WITH (FORMAT csv, DELIMITER E'\t');"

# Create indexes
echo "Creating GeoNames indexes..."
psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -c "UPDATE geonames SET geom = ST_SetSRID(ST_MakePoint(longitude::double precision, latitude::double precision), 4326) WHERE geom IS NULL;" \
    -c "CREATE INDEX IF NOT EXISTS idx_geonames_geom ON geonames USING GIST (geom);" \
    -c "CREATE INDEX IF NOT EXISTS idx_geonames_name ON geonames (name);" \
    -c "CREATE INDEX IF NOT EXISTS idx_geonames_country ON geonames (country);" \
    -c "CREATE INDEX IF NOT EXISTS idx_geonames_fcode ON geonames (fcode);" \
    -c "CREATE INDEX IF NOT EXISTS idx_geonames_population ON geonames (population DESC);" \
    -c "CREATE INDEX IF NOT EXISTS idx_geonames_country_fcode ON geonames (country, fcode);" \
    -c "CREATE INDEX IF NOT EXISTS idx_geonames_country_admin1 ON geonames (country, admin1);" \
    -c "CREATE INDEX IF NOT EXISTS idx_geonames_admin1 ON geonames (admin1);" 2>&1 | grep -v "NOTICE"

unset PGPASSWORD
echo -e "${GREEN}✓${NC} GeoNames import completed"
echo ""

# Step 6: Create Postal Codes schema
echo -e "${YELLOW}Step 6: Creating Postal Codes schema${NC}"
export PGPASSWORD="$GCP_PASSWORD"
psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -f "$POSTAL_DIR/create_postal_code_schema.sql" 2>&1 | grep -v "NOTICE"
echo -e "${GREEN}✓${NC} Postal Codes schema created"
unset PGPASSWORD
echo ""

# Step 7: Import Postal Codes data
echo -e "${YELLOW}Step 7: Importing Postal Codes data (43K rows)${NC}"

cd "$POSTAL_DIR"

# Check if data files exist
if [ ! -f "allCountries_US_postal.txt" ] || [ ! -f "allCountries_CA_postal.txt" ]; then
    echo -e "${YELLOW}Data files not found. Extracting from ZIP files...${NC}"
    [ -f "US.zip" ] && unzip -o US.zip && mv US.txt allCountries_US_postal.txt
    [ -f "CA.zip" ] && unzip -o CA.zip && mv CA.txt allCountries_CA_postal.txt
fi

# Import US postal codes
echo "Importing US postal codes..."
PGPASSWORD="$GCP_PASSWORD" psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -c "\COPY postal_codes (country, postal_code, place_name, admin1_name, admin1_code, admin2_name, admin2_code, admin3_name, admin3_code, latitude, longitude, accuracy) FROM 'allCountries_US_postal.txt' WITH (FORMAT csv, DELIMITER E'\t');"

# Import Canada postal codes
echo "Importing Canada postal codes..."
PGPASSWORD="$GCP_PASSWORD" psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -c "\COPY postal_codes (country, postal_code, place_name, admin1_name, admin1_code, admin2_name, admin2_code, admin3_name, admin3_code, latitude, longitude, accuracy) FROM 'allCountries_CA_postal.txt' WITH (FORMAT csv, DELIMITER E'\t');"

# Create indexes
echo "Creating Postal Codes indexes..."
PGPASSWORD="$GCP_PASSWORD" psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" \
    -c "UPDATE postal_codes SET geom = ST_SetSRID(ST_MakePoint(longitude::double precision, latitude::double precision), 4326) WHERE geom IS NULL;" \
    -c "CREATE INDEX IF NOT EXISTS idx_postal_codes_geom ON postal_codes USING GIST (geom);" \
    -c "CREATE INDEX IF NOT EXISTS idx_postal_codes_postal_code ON postal_codes (postal_code);" \
    -c "CREATE INDEX IF NOT EXISTS idx_postal_codes_country_postal_code ON postal_codes (country, postal_code);" \
    -c "CREATE INDEX IF NOT EXISTS idx_postal_codes_place_name ON postal_codes (place_name);" \
    -c "CREATE INDEX IF NOT EXISTS idx_postal_codes_country_admin1 ON postal_codes (country, admin1_code);" 2>&1 | grep -v "NOTICE"

echo -e "${GREEN}✓${NC} Postal Codes import completed"
echo ""

# Step 8: Import US ZIP boundaries
echo -e "${YELLOW}Step 8: Importing US ZIP boundaries (33K polygons)${NC}"
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
echo "Importing boundaries to database..."
export PGPASSWORD="$GCP_PASSWORD"
shp2pgsql -s 4326 -D -I tl_2023_us_zcta520.shp temp_zcta | \
    psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" -q
unset PGPASSWORD

# Update postal_codes table with boundaries
echo "Matching boundaries to postal codes..."
export PGPASSWORD="$GCP_PASSWORD"
psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" << 'EOF'
UPDATE postal_codes pc
SET boundary = zcta.geom
FROM temp_zcta zcta
WHERE pc.country = 'US'
  AND pc.postal_code = zcta.zcta5ce20;

CREATE INDEX IF NOT EXISTS idx_postal_codes_boundary ON postal_codes USING GIST (boundary);

DROP TABLE temp_zcta;

SELECT
    COUNT(*) as total_postal_codes,
    COUNT(boundary) as with_boundaries,
    ROUND(100.0 * COUNT(boundary) / COUNT(*), 1) as boundary_coverage_pct
FROM postal_codes
WHERE country = 'US';
EOF
unset PGPASSWORD

echo -e "${GREEN}✓${NC} ZIP boundaries import completed"
echo ""

# Step 9: Verify all imports
echo -e "${YELLOW}Step 9: Verifying imports${NC}"
export PGPASSWORD="$GCP_PASSWORD"
psql -h localhost -p $PROXY_PORT -U "$GCP_USER" -d "$GCP_DB" << 'EOF'
SELECT
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
ORDER BY row_count DESC;
EOF
unset PGPASSWORD

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}Direct import completed successfully!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "All geospatial tables are now populated in GCP Cloud SQL"
echo ""
