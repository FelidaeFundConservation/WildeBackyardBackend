#!/bin/bash
set -e

# Compare row counts between local and cloud databases

echo "=== Database Row Count Comparison ==="
echo ""

# Local database counts
echo "LOCAL DATABASE (wildebackyard):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
psql -d wildebackyard -t -c "
SELECT
    table_name,
    to_char(row_count, '999,999,999') as rows
FROM (
    SELECT 'admin1_codes' as table_name, COUNT(*) as row_count FROM admin1_codes
    UNION ALL
    SELECT 'feature_codes', COUNT(*) FROM feature_codes
    UNION ALL
    SELECT 'geonames', COUNT(*) FROM geonames
    UNION ALL
    SELECT 'postal_codes (total)', COUNT(*) FROM postal_codes
    UNION ALL
    SELECT 'postal_codes (w/boundaries)', COUNT(*) FROM postal_codes WHERE boundary IS NOT NULL
) counts
ORDER BY table_name;
"
echo ""

# Start Cloud SQL Proxy
echo "Starting Cloud SQL Proxy..."
cloud_sql_proxy -instances=wildepod-339517:us-west2:wildepoddb=tcp:5434 > /tmp/verify_proxy.log 2>&1 &
PROXY_PID=$!
sleep 5

echo "CLOUD DATABASE (GCP wildebackyard_api_staging):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
export PGPASSWORD="/REDACTED="
psql -h localhost -p 5434 -U wildepod_wildebackyard_api_user -d wildebackyard_api_staging -t -c "
SELECT
    table_name,
    to_char(row_count, '999,999,999') as rows
FROM (
    SELECT 'admin1_codes' as table_name, COUNT(*) as row_count FROM admin1_codes
    UNION ALL
    SELECT 'feature_codes', COUNT(*) FROM feature_codes
    UNION ALL
    SELECT 'geonames', COUNT(*) FROM geonames
    UNION ALL
    SELECT 'postal_codes (total)', COUNT(*) FROM postal_codes
    UNION ALL
    SELECT 'postal_codes (w/boundaries)', COUNT(*) FROM postal_codes WHERE boundary IS NOT NULL
) counts
ORDER BY table_name;
"
unset PGPASSWORD

# Stop proxy
kill $PROXY_PID 2>/dev/null

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Comparison complete!"
echo ""
