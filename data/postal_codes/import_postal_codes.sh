#!/bin/bash
# Import GeoNames postal code data for US and Canada
# Data source: http://download.geonames.org/export/zip/

set -e  # Exit on error

DB_NAME="wildebackyard"
DB_USER="${PGUSER:-jnovak}"

echo "Downloading postal code data..."
# US postal codes (~41K records)
wget -N http://download.geonames.org/export/zip/US.zip
# Canada postal codes (~1.6M FSA/FSA+LDU records)
wget -N http://download.geonames.org/export/zip/CA.zip

echo "Extracting postal code files..."
unzip -o US.zip
unzip -o CA.zip

echo "Creating database schema..."
psql -d "$DB_NAME" -U "$DB_USER" -f create_postal_code_schema.sql

echo "Importing US postal codes..."
psql -d "$DB_NAME" -U "$DB_USER" << 'EOF'
\COPY postal_codes (country, postal_code, place_name, admin1_name, admin1_code, admin2_name, admin2_code, admin3_name, admin3_code, latitude, longitude, accuracy) FROM 'US.txt' WITH (FORMAT csv, DELIMITER E'\t', NULL '', QUOTE E'\b', ENCODING 'UTF8');
EOF

echo "Importing CA postal codes..."
psql -d "$DB_NAME" -U "$DB_USER" << 'EOF'
\COPY postal_codes (country, postal_code, place_name, admin1_name, admin1_code, admin2_name, admin2_code, admin3_name, admin3_code, latitude, longitude, accuracy) FROM 'CA.txt' WITH (FORMAT csv, DELIMITER E'\t', NULL '', QUOTE E'\b', ENCODING 'UTF8');
EOF

echo "Updating PostGIS geometry column from lat/lon..."
psql -d "$DB_NAME" -U "$DB_USER" << 'EOF'
UPDATE postal_codes
SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326);
EOF

echo "Analyzing table for query optimization..."
psql -d "$DB_NAME" -U "$DB_USER" << 'EOF'
ANALYZE postal_codes;
EOF

echo "Import complete!"
psql -d "$DB_NAME" -U "$DB_USER" << 'EOF'
SELECT
    country,
    COUNT(*) as total_codes,
    MIN(postal_code) as first_code,
    MAX(postal_code) as last_code
FROM postal_codes
GROUP BY country
ORDER BY country;
EOF
