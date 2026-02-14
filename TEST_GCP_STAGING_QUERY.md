# GCP Staging Database Query Test

## ⚠️ CRITICAL: This Test ONLY Runs Against GCP Staging Database

This test is **specifically designed** to query the **actual GCP staging database**, NOT a local database.

## Overview

Test file: `siteapps/users/test_gcp_staging_connectivity.py`

This test will **FAIL** if not properly connected to the GCP staging database to prevent accidental queries against local databases.

## Required Configuration

### 1. Settings Module (REQUIRED)
```bash
--settings=config.settings.wildebackyard_api
```

### 2. Database URL (REQUIRED)
```bash
export WILDEBACKYARD_API_DATABASE_URL='postgres://wildepod_wildebackyard_api_user:PASSWORD@127.0.0.1:5432/wildebackyard_api_staging'
```

### 3. Cloud SQL Proxy (REQUIRED)
```bash
cloud-sql-proxy wildepod-339517:us-west2:wildepoddb --port 5432
```

## Safety Features

The test includes multiple checks to ensure it only runs against GCP staging:

1. ✅ **Verifies settings module** is `config.settings.wildebackyard_api`
2. ✅ **Verifies database URL** is set (WILDEBACKYARD_API_DATABASE_URL)
3. ✅ **Verifies database name** is `wildebackyard_api_staging`
4. ❌ **FAILS immediately** if any requirement is not met

### Example Failure Messages

If wrong settings:
```
❌ WRONG SETTINGS MODULE: config.settings.local
This test MUST use config.settings.wildebackyard_api
Run with: --settings=config.settings.wildebackyard_api
```

If database URL not set:
```
❌ WILDEBACKYARD_API_DATABASE_URL not set!
This test requires connection to GCP staging database.
Make sure Cloud SQL Proxy is running!
```

If wrong database:
```
❌ WRONG DATABASE: wildebackyard
This test MUST connect to 'wildebackyard_api_staging'
```

## Running the Test

### Prerequisites

1. **Cloud SQL Proxy running**:
   ```bash
   cloud-sql-proxy wildepod-339517:us-west2:wildepoddb --port 5432
   ```

2. **Database credentials** (get from Secret Manager):
   ```bash
   gcloud secrets versions access latest --secret=wildebackyard_api_db_password
   ```

3. **Environment variable set**:
   ```bash
   export WILDEBACKYARD_API_DATABASE_URL='postgres://wildepod_wildebackyard_api_user:PASSWORD@127.0.0.1:5432/wildebackyard_api_staging'
   ```

### Method 1: Run with Django Test Runner (Recommended)

```bash
# Run all tests in the connectivity test file
python manage.py test siteapps.users.test_gcp_staging_connectivity \
    --settings=config.settings.wildebackyard_api

# Run specific test to query for user
python manage.py test siteapps.users.test_gcp_staging_connectivity.GCPStagingConnectivityTest.test_query_target_user \
    --settings=config.settings.wildebackyard_api

# Run with verbose output
python manage.py test siteapps.users.test_gcp_staging_connectivity \
    --settings=config.settings.wildebackyard_api \
    -v 2

# Keep test database (for debugging)
python manage.py test siteapps.users.test_gcp_staging_connectivity \
    --settings=config.settings.wildebackyard_api \
    --keepdb
```

### Method 2: Run with pytest

```bash
# Install pytest if needed
pip install pytest pytest-django

# Run tests
pytest siteapps/users/test_gcp_staging_connectivity.py -v -s

# Run specific test
pytest siteapps/users/test_gcp_staging_connectivity.py::GCPStagingConnectivityTest::test_query_target_user -v -s
```

### Method 3: Complete Setup Script

```bash
#!/bin/bash
# save as run_staging_test.sh

# Terminal 1 setup (run in background or separate terminal)
cloud-sql-proxy wildepod-339517:us-west2:wildepoddb --port 5432 &
PROXY_PID=$!
sleep 3

# Get credentials
DB_PASSWORD=$(gcloud secrets versions access latest --secret=wildebackyard_api_db_password)

# Set environment
export WILDEBACKYARD_API_DATABASE_URL="postgres://wildepod_wildebackyard_api_user:${DB_PASSWORD}@127.0.0.1:5432/wildebackyard_api_staging"

# Run the test
python manage.py test siteapps.users.test_gcp_staging_connectivity \
    --settings=config.settings.wildebackyard_api \
    -v 2

# Cleanup
kill $PROXY_PID
```

## Test Classes

### GCPStagingConnectivityTest
Main test class with connectivity tests:

- **test_database_connection**: Verifies database connection is working
- **test_query_target_user**: Queries for `jnovak@example.com` specifically
- **test_user_model_structure**: Verifies User model has expected fields

### GCPStagingDatabaseInfoTest
Informational test that displays configuration:

- **test_display_database_info**: Shows database configuration details

## Expected Output

### Success - User Found
```
======================================================================
QUERY FOR USER: jnovak@example.com
======================================================================

Django ORM Query:
  User.objects.get(email='jnovak@example.com')

Equivalent SQL:
  SELECT * FROM users_user WHERE email = 'jnovak@example.com';

Total users in database: 42

======================================================================
✅ SUCCESS - USER FOUND!
======================================================================

User Details:
  ID:         <uuid>
  Email:      jnovak@example.com
  Name:       John Novak
  Active:     True
  Staff:      False
  Superuser:  False
  Warnings:   0
  Bio:        ...
  Created:    2024-01-15 10:30:00
  Modified:   2024-01-20 14:25:00

======================================================================
✅ GCP STAGING DATABASE CONNECTIVITY VERIFIED
======================================================================

.
----------------------------------------------------------------------
Ran 1 test in 0.234s

OK
```

### User Not Found (But Database Connected)
```
⚠️  User 'jnovak@example.com' NOT FOUND in database

First 5 users in database:
  1. admin@example.com                 | Admin User
  2. test@example.com                  | Test User
  ...

Searching for emails containing 'jnovak'...
  None found

Searching for emails with '@example.com'...
Found:
  - admin@example.com                 | Admin User
  - test@example.com                  | Test User

======================================================================
✅ Database accessible but user 'jnovak@example.com' not found
======================================================================

s
----------------------------------------------------------------------
Ran 1 test in 0.156s

OK (skipped=1)
```

### Connection Failed
```
❌ Database connection failed: connection to server at "localhost"...

F
----------------------------------------------------------------------
Ran 1 test in 0.012s

FAILED (failures=1)
```

## Integration with CI/CD

To integrate this test into your CI/CD pipeline:

1. **Add to GitHub Actions**:
   ```yaml
   - name: Run GCP Staging Connectivity Test
     env:
       WILDEBACKYARD_API_DATABASE_URL: ${{ secrets.STAGING_DATABASE_URL }}
     run: |
       python manage.py test siteapps.users.test_gcp_staging_connectivity \
         --settings=config.settings.wildebackyard_api
   ```

2. **Add as deployment verification**:
   Run after deployment to verify staging database is accessible

3. **Monitor regularly**:
   Schedule periodic runs to ensure database connectivity

## Test Behavior

- ✅ **User found**: Test passes
- ⚠️ **User not found**: Test is skipped (database works, user just doesn't exist)
- ❌ **Connection failed**: Test fails (database not accessible)

This approach ensures the test doesn't fail unnecessarily when the user doesn't exist, but still verifies database connectivity.

## Troubleshooting

### Test can't find Django settings
```bash
# Make sure to specify settings module
python manage.py test ... --settings=config.settings.wildebackyard_api
```

### Connection refused
```bash
# Verify Cloud SQL Proxy is running
ps aux | grep cloud-sql-proxy

# Start it if not running
cloud-sql-proxy wildepod-339517:us-west2:wildepoddb --port 5432
```

### Authentication failed
```bash
# Get fresh password
gcloud secrets versions access latest --secret=wildebackyard_api_db_password

# Verify you're authenticated with GCP
gcloud auth list
```

### Test database creation fails
```bash
# Use --keepdb to reuse existing test database
python manage.py test ... --keepdb

# Or skip database creation (read-only test)
# The test doesn't require migrations, just queries existing data
```

## Files

- **Test file**: `siteapps/users/test_gcp_staging_connectivity.py`
- **This guide**: `TEST_GCP_STAGING_QUERY.md`
- **User model**: `siteapps/users/models.py`
- **Settings**: `config/settings/wildebackyard_api.py`

## Notes

- This test queries the **real staging database**
- It's read-only (no data is created or modified)
- Can be safely run multiple times
- Part of the standard Django test suite
- Uses existing test infrastructure
- Compatible with pytest and Django test runner
