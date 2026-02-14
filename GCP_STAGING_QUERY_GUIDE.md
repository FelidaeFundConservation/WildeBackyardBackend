# GCP Staging Database Query - ACTUAL EXECUTION GUIDE

## Objective
Query the GCP staging database for user `jnovak@example.com` to verify database connectivity.

## Quick Start - Run the Query NOW

### Prerequisites
1. GCP account with access to `wildepod-339517` project
2. Cloud SQL Proxy installed
3. Python dependencies installed

### Step-by-Step Execution

#### Terminal 1: Start Cloud SQL Proxy

```bash
# Authenticate with GCP
gcloud auth login
gcloud config set project wildepod-339517

# Install Cloud SQL Proxy if needed
curl -o cloud-sql-proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64
chmod +x cloud-sql-proxy

# Start the proxy
./cloud-sql-proxy wildepod-339517:us-west2:wildepoddb --port 5432
```

Keep this terminal running!

#### Terminal 2: Run the Query

```bash
# Navigate to project
cd /path/to/WildeBackyardBackend

# Get database password from Secret Manager
DB_PASSWORD=$(gcloud secrets versions access latest --secret=wildebackyard_api_db_password)

# Set database URL
export WILDEBACKYARD_API_DATABASE_URL="postgres://wildepod_wildebackyard_api_user:${DB_PASSWORD}@127.0.0.1:5432/wildebackyard_api_staging"

# Run the query script
python run_gcp_staging_query.py
```

## Expected Output

### If User Exists (Success)
```
================================================================================
✅ SUCCESS! USER FOUND IN GCP STAGING DATABASE
================================================================================

USER DETAILS:
  ID:           <uuid>
  Email:        jnovak@example.com
  Name:         <name>
  Active:       True
  Staff:        False/True
  Superuser:    False/True
  Warnings:     0
  Bio:          <bio text>
  Created:      <timestamp>
  Modified:     <timestamp>

================================================================================
✅ GCP STAGING DATABASE CONNECTIVITY VERIFIED
================================================================================
```

### If User Not Found (But Database Connected)
```
⚠️  User 'jnovak@example.com' NOT FOUND in database

Total users in database: X

First 5 users in database:
  1. user1@example.com              | User One
  2. user2@example.com              | User Two
  ...

================================================================================
✅ Database connected successfully but user not found
================================================================================
```

## Alternative Methods

### Method 1: Django Shell
```bash
# Start Cloud SQL Proxy (Terminal 1)
./cloud-sql-proxy wildepod-339517:us-west2:wildepoddb --port 5432

# Set environment and run Django shell (Terminal 2)
export WILDEBACKYARD_API_DATABASE_URL="postgres://USER:PASSWORD@127.0.0.1:5432/wildebackyard_api_staging"
python manage.py shell --settings=config.settings.wildebackyard_api

# In Django shell:
from siteapps.users.models import User
user = User.objects.get(email='jnovak@example.com')
print(f"Found: {user.name} ({user.email})")
```

### Method 2: Direct SQL via gcloud
```bash
# Connect to database
gcloud sql connect wildepoddb \
  --user=wildepod_wildebackyard_api_user \
  --database=wildebackyard_api_staging

# At the psql prompt:
SELECT id, email, name, is_active, created 
FROM users_user 
WHERE email = 'jnovak@example.com';
```

### Method 3: Direct SQL via psql (with Cloud SQL Proxy)
```bash
# Terminal 1: Start proxy
./cloud-sql-proxy wildepod-339517:us-west2:wildepoddb --port 5432

# Terminal 2: Connect with psql
PGPASSWORD='<password>' psql \
  -h 127.0.0.1 \
  -p 5432 \
  -U wildepod_wildebackyard_api_user \
  -d wildebackyard_api_staging \
  -c "SELECT * FROM users_user WHERE email = 'jnovak@example.com';"
```

## Query Details

### Django ORM Query
```python
from siteapps.users.models import User
user = User.objects.get(email='jnovak@example.com')
```

### Raw SQL Query
```sql
SELECT 
    id, email, name, is_active, is_staff, 
    is_superuser, warnings, bio, created, modified
FROM users_user 
WHERE email = 'jnovak@example.com';
```

### Table Structure
- **Table Name**: `users_user`
- **Email Field**: `email` (EmailField, unique=True)
- **Primary Key**: `id` (UUID)
- **Model**: `siteapps.users.models.User`

## Database Configuration

- **GCP Project**: `wildepod-339517`
- **Instance**: `wildepod-339517:us-west2:wildepoddb`
- **Database**: `wildebackyard_api_staging`
- **User**: `wildepod_wildebackyard_api_user`
- **Region**: `us-west2`
- **Connection**: Unix socket `/cloudsql/wildepod-339517:us-west2:wildepoddb` (on GCP)
- **Connection**: `127.0.0.1:5432` (via Cloud SQL Proxy)

## Troubleshooting

### Error: "cloud-sql-proxy: command not found"
```bash
# Download Cloud SQL Proxy
curl -o cloud-sql-proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64
chmod +x cloud-sql-proxy
sudo mv cloud-sql-proxy /usr/local/bin/
```

### Error: "permission denied for secret"
```bash
# Ensure you have access to Secret Manager
gcloud projects add-iam-policy-binding wildepod-339517 \
  --member="user:YOUR_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

### Error: "connection refused"
- Verify Cloud SQL Proxy is running: `ps aux | grep cloud-sql-proxy`
- Check proxy is listening: `netstat -an | grep 5432`
- Verify instance name is correct: `gcloud sql instances list`

### Error: "password authentication failed"
- Get fresh password: `gcloud secrets versions access latest --secret=wildebackyard_api_db_password`
- Verify user exists: `gcloud sql users list --instance=wildepoddb`
- Check user permissions in database

### Connection hangs or times out
- Check firewall rules for Cloud SQL
- Verify you have `roles/cloudsql.client` IAM role
- Try direct gcloud connection: `gcloud sql connect wildepoddb`

## Security Notes

⚠️ **Important Security Practices**:
- Never commit database passwords to git
- Use GCP Secret Manager for credentials
- Use Cloud SQL Proxy for secure connections
- Rotate passwords regularly
- Use least privilege IAM roles
- Enable Cloud SQL audit logging

## Files in This Repository

1. **run_gcp_staging_query.py** - Main query script (run this!)
2. **query_staging_user.py** - Alternative query script
3. **test_staging_db_connectivity.py** - Connectivity test script
4. **run_staging_db_test.sh** - Bash wrapper script
5. **GCP_STAGING_QUERY_GUIDE.md** - This file
6. **GCP_STAGING_DB_TEST.md** - Detailed testing guide
7. **DB_TEST_README.md** - Quick reference

## Next Steps

After successfully querying the database:

1. **Document the result**: Did you find the user? Update the issue with findings.
2. **Check user details**: Verify the user has expected properties.
3. **Test other queries**: Try querying by ID or other fields.
4. **Run migrations**: If needed, apply database migrations.
5. **Monitor performance**: Check query execution time and logs.

## Support

For issues or questions:
- Check GCP Cloud SQL logs: `gcloud sql operations list --instance=wildepoddb`
- View application logs: `gcloud app logs read --service=wildebackyard-api`
- Consult GCP_DEPLOYMENT_REFERENCE.md for deployment details
