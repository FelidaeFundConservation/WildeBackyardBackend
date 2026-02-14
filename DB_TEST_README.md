# Database Connectivity Test Files

This directory contains scripts and documentation for testing GCP staging database connectivity.

## Files Overview

### 1. `test_staging_db_connectivity.py`
**Purpose**: Python script to query the GCP staging database for user `jnovak@example.com`

**Usage**:
```bash
# Set database URL first
export WILDEBACKYARD_API_DATABASE_URL='postgres://USER:PASSWORD@127.0.0.1:5432/wildebackyard_api_staging'

# Run the test
python test_staging_db_connectivity.py
```

**What it does**:
- Connects to GCP staging database
- Queries for user with email `jnovak@example.com`
- Reports user details if found
- Shows total user count if not found
- Validates database connectivity

### 2. `run_staging_db_test.sh`
**Purpose**: Bash wrapper script for easy testing

**Usage**:
```bash
# Make sure Cloud SQL Proxy is running first
cloud-sql-proxy --port 5432 wildepod-339517:us-west2:wildepoddb

# In another terminal, run the test
./run_staging_db_test.sh
```

**What it does**:
- Checks prerequisites
- Validates environment variables
- Runs the Python test script
- Reports results

### 3. `GCP_STAGING_DB_TEST.md`
**Purpose**: Comprehensive documentation

**Contents**:
- Database connection information
- Multiple methods to execute queries
- Troubleshooting guide
- Security best practices

## Quick Start

### Prerequisites
1. Install Cloud SQL Proxy
2. Install Python dependencies: `pip install -r requirements.txt`
3. Get database password from GCP Secret Manager

### Steps

**Terminal 1 - Start Cloud SQL Proxy:**
```bash
cloud-sql-proxy --port 5432 wildepod-339517:us-west2:wildepoddb
```

**Terminal 2 - Run Test:**
```bash
# Get password from Secret Manager
gcloud secrets versions access latest --secret="wildebackyard_api_db_password"

# Set environment variable (replace PASSWORD)
export WILDEBACKYARD_API_DATABASE_URL='postgres://wildepod_wildebackyard_api_user:PASSWORD@127.0.0.1:5432/wildebackyard_api_staging'

# Run test script
python test_staging_db_connectivity.py
```

## Query Details

**Target User**: `jnovak@example.com`

**Django ORM**:
```python
from siteapps.users.models import User
user = User.objects.get(email='jnovak@example.com')
```

**SQL**:
```sql
SELECT * FROM users_user WHERE email = 'jnovak@example.com';
```

## Expected Output

### Success (User Found):
```
✅ USER FOUND!

User Details:
  ID:       <UUID>
  Email:    jnovak@example.com
  Name:     <User's Name>
  Active:   True
  ...

✅ Database connectivity test PASSED
```

### Success (User Not Found):
```
❌ User with email 'jnovak@example.com' NOT FOUND in database
Total users in database: <count>

⚠️  Database connectivity is working, but this specific user was not found.
```

### Failure:
```
❌ Error connecting to database: <error message>

Common issues:
  - Cloud SQL Proxy not running
  - Incorrect DATABASE_URL
  - Network connectivity issues
```

## Alternative Methods

### Using Django Shell:
```bash
python manage.py shell --settings=config.settings.wildebackyard_api
```
```python
from siteapps.users.models import User
user = User.objects.get(email='jnovak@example.com')
print(f"User: {user.name} ({user.email})")
```

### Using psql:
```bash
psql "host=127.0.0.1 port=5432 dbname=wildebackyard_api_staging user=wildepod_wildebackyard_api_user"
```
```sql
SELECT * FROM users_user WHERE email = 'jnovak@example.com';
```

### From GCP Console:
```bash
gcloud sql connect wildepoddb --user=wildepod_wildebackyard_api_user --database=wildebackyard_api_staging
```

## Troubleshooting

See `GCP_STAGING_DB_TEST.md` for detailed troubleshooting steps.

Common issues:
- Cloud SQL Proxy not running → Start it first
- Wrong password → Get from Secret Manager
- Connection timeout → Check network/firewall
- Permission denied → Verify IAM roles

## Security

⚠️ **Important**:
- Never commit database passwords
- Use environment variables
- Store secrets in GCP Secret Manager
- Use Cloud SQL Proxy for secure connections

## Related Documentation

- [GCP_DEPLOYMENT_REFERENCE.md](./GCP_DEPLOYMENT_REFERENCE.md) - Main deployment reference
- [GCP_STAGING_DB_TEST.md](./GCP_STAGING_DB_TEST.md) - Detailed testing guide
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Quick command reference
