#!/bin/bash
# Import Canadian Forward Sortation Area (FSA) boundaries
# FSA = first 3 characters of postal code (e.g., K1A, M5V, V6B)

set -e

DB_NAME="wildebackyard"
DB_USER="${PGUSER:-jnovak}"

echo "=== Canadian Postal Code Boundary Import ==="
echo ""
echo "Canadian postal code boundaries are available at FSA (Forward Sortation Area) level."
echo "FSA is the first 3 characters of a postal code (e.g., K1A, M5V)."
echo ""
echo "Data sources:"
echo "1. Statistics Canada (free, registration required):"
echo "   https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index-eng.cfm"
echo "2. GeoNames Canada FSA boundaries (if available)"
echo "3. Commercial sources (DMTI, etc.)"
echo ""
echo "Manual steps:"
echo "1. Download FSA boundary shapefile from Statistics Canada"
echo "2. Extract to this directory"
echo "3. Run: shp2pgsql -s 4326 -I -D lfsa000b21a_e.shp temp_fsa_boundaries | psql -d $DB_NAME -U $DB_USER"
echo "4. Match boundaries to postal codes by FSA prefix:"
echo ""
cat << 'SQL'
-- Update Canadian postal codes with FSA boundaries
UPDATE postal_codes pc
SET boundary = fb.geom
FROM temp_fsa_boundaries fb
WHERE pc.country = 'CA'
  AND LEFT(pc.postal_code, 3) = fb.cfsauid;  -- Match first 3 chars

-- Show statistics
SELECT
    COUNT(*) FILTER (WHERE boundary IS NOT NULL) as with_boundaries,
    COUNT(*) FILTER (WHERE boundary IS NULL) as without_boundaries,
    COUNT(*) as total
FROM postal_codes
WHERE country = 'CA';

-- Clean up
DROP TABLE temp_fsa_boundaries;
SQL

echo ""
echo "Due to registration requirements, automatic download is not implemented."
echo "Please download manually from Statistics Canada."
