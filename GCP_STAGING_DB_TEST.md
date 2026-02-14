# GCP Staging Database Connectivity Test

## Purpose
This document describes how to verify connectivity to the GCP staging database by querying for a specific user (`jnovak@example.com`).

## Database Information

- **Database Name**: `wildebackyard_api_staging`
- **Cloud SQL Instance**: `wildepod-339517:us-west2:wildepoddb`
- **Database User**: `wildepod_wildebackyard_api_user`
- **User Table**: `users_user`
- **Settings Module**: `config.settings.wildebackyard_api`

## Query Details

### Django ORM Query
```python
from siteapps.users.models import User
user = User.objects.get(email='jnovak@example.com')
print(f"User: {user.name} ({user.email})")
print(f"ID: {user.id}")
print(f"Active: {user.is_active}")
```

### Raw SQL Query
```sql
SELECT 
    id,
    email,
    name,
    is_active,
    is_staff,
    is_superuser,
    warnings,
    bio,
    created,
    modified
FROM users_user
WHERE email = 'jnovak@example.com';
```

## How to Execute the Query

### Option 1: Using the Test Script (Recommended)

1. **Start Cloud SQL Proxy**
   ```bash
   cloud-sql-proxy --port 5432 wildepod-339517:us-west2:wildepoddb
   ```

2. **Set Database URL**
   ```bash
   # Replace PASSWORD with actual password from GCP Secret Manager
   export WILDEBACKYARD_API_DATABASE_URL='postgres://wildepod_wildebackyard_api_user:PASSWORD@127.0.0.1:5432/wildebackyard_api_staging'
   ```

3. **Run Test Script**
   ```bash
   python test_staging_db_connectivity.py
   ```

### Option 2: Using Django Shell

1. **Start Cloud SQL Proxy** (same as above)

2. **Set Database URL** (same as above)

3. **Open Django Shell**
   ```bash
   python manage.py shell --settings=config.settings.wildebackyard_api
   ```

4. **Execute Query**
   ```python
   from siteapps.users.models import User
   
   # Query for the user
   try:
       user = User.objects.get(email='jnovak@example.com')
       print(f"✅ User found!")
       print(f"Name: {user.name}")
       print(f"Email: {user.email}")
       print(f"ID: {user.id}")
       print(f"Active: {user.is_active}")
       print(f"Staff: {user.is_staff}")
   except User.DoesNotExist:
       print("❌ User not found")
       print(f"Total users: {User.objects.count()}")
   ```

### Option 3: Using psql (Direct SQL)

1. **Start Cloud SQL Proxy** (same as above)

2. **Connect with psql**
   ```bash
   # Replace PASSWORD with actual password
   psql "host=127.0.0.1 port=5432 dbname=wildebackyard_api_staging user=wildepod_wildebackyard_api_user password=PASSWORD"
   ```

3. **Run SQL Query**
   ```sql
   SELECT * FROM users_user WHERE email = 'jnovak@example.com';
   ```

### Option 4: From GCP Console (No Local Setup Required)

1. **Go to Cloud SQL in GCP Console**
   - Navigate to: https://console.cloud.google.com/sql/instances
   - Select instance: `wildepoddb`

2. **Open Cloud Shell or connect via gcloud**
   ```bash
   gcloud sql connect wildepoddb --user=wildepod_wildebackyard_api_user --database=wildebackyard_api_staging
   ```

3. **Run Query**
   ```sql
   SELECT id, email, name, is_active FROM users_user WHERE email = 'jnovak@example.com';
   ```

## Expected Results

### If User Exists
```
✅ USER FOUND!

User Details:
  ID:       <UUID>
  Email:    jnovak@example.com
  Name:     <User's Name>
  Active:   True
  Staff:    False/True
  Superuser: False/True
  Warnings: 0
  Created:  <timestamp>
  Modified: <timestamp>

✅ Database connectivity test PASSED
```

### If User Does Not Exist
```
❌ User with email 'jnovak@example.com' NOT FOUND in database

Total users in database: <count>

⚠️  The user 'jnovak@example.com' does not exist in the staging database.
   Database connectivity is working, but this specific user was not found.
```

## Troubleshooting

### Cloud SQL Proxy Issues
- **Error**: "dial tcp: lookup wildepod-339517 on [::1]:53: no such host"
  - **Solution**: Verify the instance connection name is correct
  - Check: `gcloud sql instances describe wildepoddb --format="value(connectionName)"`

- **Error**: "unable to connect to Cloud SQL"
  - **Solution**: Ensure you have the correct IAM permissions
  - Required role: `roles/cloudsql.client`

### Authentication Issues
- **Error**: "password authentication failed"
  - **Solution**: Get the correct password from GCP Secret Manager:
    ```bash
    gcloud secrets versions access latest --secret="wildebackyard_api_db_password"
    ```

### Connection Issues
- **Error**: "could not connect to server"
  - **Solution**: Verify Cloud SQL Proxy is running: `ps aux | grep cloud-sql-proxy`
  - Check proxy logs for errors

## Security Notes

- ⚠️ **Never commit database credentials** to the repository
- Store passwords in GCP Secret Manager
- Use Cloud SQL Proxy for secure local connections
- Rotate database credentials regularly
- Use read-only database users for testing when possible

## Files Created

1. **test_staging_db_connectivity.py** - Python script to test connectivity
2. **GCP_STAGING_DB_TEST.md** - This documentation file

## Additional Resources

- [GCP Cloud SQL Proxy Documentation](https://cloud.google.com/sql/docs/postgres/sql-proxy)
- [Django Database Documentation](https://docs.djangoproject.com/en/5.0/ref/databases/)
- [GCP_DEPLOYMENT_REFERENCE.md](./GCP_DEPLOYMENT_REFERENCE.md) - Main deployment reference
