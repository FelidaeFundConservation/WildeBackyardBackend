#!/bin/bash
#
# Quick commands to test GCP staging database connectivity
# Query for user: jnovak@example.com
#

set -e

echo "=========================================="
echo "GCP Staging Database Query - Quick Start"
echo "=========================================="
echo

# Check if Cloud SQL Proxy is available
if ! command -v cloud-sql-proxy &> /dev/null; then
    echo "⚠️  Cloud SQL Proxy not found. Install it first:"
    echo "   https://cloud.google.com/sql/docs/postgres/sql-proxy#install"
    echo
    exit 1
fi

# Check if DATABASE_URL is set
if [ -z "$WILDEBACKYARD_API_DATABASE_URL" ]; then
    echo "⚠️  WILDEBACKYARD_API_DATABASE_URL not set"
    echo
    echo "Steps to run this test:"
    echo
    echo "1. In Terminal 1 - Start Cloud SQL Proxy:"
    echo "   cloud-sql-proxy --port 5432 wildepod-339517:us-west2:wildepoddb"
    echo
    echo "2. In Terminal 2 - Get password from Secret Manager:"
    echo "   gcloud secrets versions access latest --secret=\"wildebackyard_api_db_password\""
    echo
    echo "3. Set environment variable (replace PASSWORD):"
    echo "   export WILDEBACKYARD_API_DATABASE_URL='postgres://wildepod_wildebackyard_api_user:PASSWORD@127.0.0.1:5432/wildebackyard_api_staging'"
    echo
    echo "4. Run this script again:"
    echo "   ./run_staging_db_test.sh"
    echo
    exit 1
fi

echo "✓ Environment configured"
echo "  Database URL is set"
echo

# Run the Python test script
python test_staging_db_connectivity.py

exit_code=$?

echo
if [ $exit_code -eq 0 ]; then
    echo "=========================================="
    echo "✅ Database connectivity test SUCCESSFUL"
    echo "=========================================="
elif [ $exit_code -eq 2 ]; then
    echo "=========================================="
    echo "⚠️  Database accessible but user not found"
    echo "=========================================="
else
    echo "=========================================="
    echo "❌ Database connectivity test FAILED"
    echo "=========================================="
fi

exit $exit_code
