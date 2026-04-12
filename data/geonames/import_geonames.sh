#!/bin/bash
# Import GeoNames data into PostgreSQL
# Run from: /home/jnovak/Projects/WildeBackyardBackend/data/geonames/

set -e

echo "Importing admin1 codes (states/provinces)..."
psql -d wildebackyard -c "\COPY admin1_codes FROM 'admin1CodesASCII.txt' WITH (FORMAT csv, DELIMITER E'\t', QUOTE E'\b', HEADER false)"

echo "Importing feature codes..."
psql -d wildebackyard -c "\COPY feature_codes FROM 'featureCodes_en.txt' WITH (FORMAT csv, DELIMITER E'\t', QUOTE E'\b', HEADER false)"

echo "Importing US geonames data (this will take several minutes)..."
psql -d wildebackyard -c "\COPY geonames(geonameid, name, asciiname, alternatenames, latitude, longitude, fclass, fcode, country, cc2, admin1, admin2, admin3, admin4, population, elevation, gtopo30, timezone, moddate) FROM 'US.txt' WITH (FORMAT csv, DELIMITER E'\t', QUOTE E'\b', NULL '', HEADER false)"

echo "Importing CA geonames data..."
psql -d wildebackyard -c "\COPY geonames(geonameid, name, asciiname, alternatenames, latitude, longitude, fclass, fcode, country, cc2, admin1, admin2, admin3, admin4, population, elevation, gtopo30, timezone, moddate) FROM 'CA.txt' WITH (FORMAT csv, DELIMITER E'\t', QUOTE E'\b', NULL '', HEADER false)"

echo "Updating PostGIS geometry column..."
psql -d wildebackyard -c "UPDATE geonames SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326);"

echo "Analyzing tables for query optimization..."
psql -d wildebackyard -c "ANALYZE geonames; ANALYZE admin1_codes; ANALYZE feature_codes;"

echo "Import complete!"
echo "US records: $(psql -d wildebackyard -t -c "SELECT COUNT(*) FROM geonames WHERE country = 'US';")"
echo "CA records: $(psql -d wildebackyard -t -c "SELECT COUNT(*) FROM geonames WHERE country = 'CA';")"
echo "Total records: $(psql -d wildebackyard -t -c "SELECT COUNT(*) FROM geonames;")"
