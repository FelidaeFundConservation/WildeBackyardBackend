# GCP Deployment Reference - ACTUAL WORKING CONFIGURATION

**Last verified working:** Version 20260203t104123

## CRITICAL: Always Check Working Version First

Before deploying, check what the last working version actually used:
```bash
gcloud app versions describe 20260203t104123 --service=wildebackyard-api --format=yaml
```

## Correct Deployment Process

### 1. Correct Directory
```bash
cd /home/jnovak/Projects/WildeBackyardBackend  # PROJECT ROOT, not gcp_deployment/
```

### 2. Correct File Location
- Use: `app.yaml` in project root
- NOT: `gcp_deployment/staging.yaml` (lacks access to requirements.txt)

### 3. Deployment Command
```bash
gcloud app deploy app.yaml --quiet
```

## Working Configuration (app.yaml)

```yaml
runtime: python310
service: wildebackyard-api
instance_class: F2
entrypoint: gunicorn -t 2400 -b :$PORT config.wsgi.wildebackyard_api:application

env_variables:
  DJANGO_SETTINGS_MODULE: "config.settings.wildebackyard_api"
  PYTHON_ENV: "production"
  CLOUD_SQL_CONNECTION_NAME: "wildepod-339517:us-west2:wildepoddb"
  WILDEBACKYARD_API_DATABASE_URL: "postgres://wildepod_wildebackyard_api_user:%2FREDACTED%2BP%2BMU%3D@/wildebackyard_api_staging"

automatic_scaling:
  min_idle_instances: 0
  max_idle_instances: 2
  min_pending_latency: 1000ms
  max_pending_latency: 3000ms
  max_concurrent_requests: 50
```

**IMPORTANT:** The DATABASE_URL should NOT include the `host` parameter in the query string. The host is set dynamically by `config/settings/wildebackyard_api.py` based on the `GAE_APPLICATION` environment variable.

## Key Points

1. **Settings Module:** Uses `config.settings.wildebackyard_api` NOT `config.settings.staging`
2. **WSGI:** Uses `config.wsgi.wildebackyard_api:application`
3. **Database:** Password is URL-encoded in WILDEBACKYARD_API_DATABASE_URL
4. **Requirements:** Deploys from root so requirements.txt is included (installs gunicorn)
5. **Storage:** Uses GCS via direct google.cloud.storage client, not Django storage backend

## Database Configuration

- **Engine:** PostgreSQL via Cloud SQL
- **Connection:** Unix socket `/cloudsql/wildepod-339517:us-west2:wildepoddb`
- **Database:** wildebackyard_api_staging
- **User:** wildepod_wildebackyard_api_user
- **Password:** In WILDEBACKYARD_API_DATABASE_URL (URL-encoded)

## Common Mistakes to Avoid

❌ Deploying from `gcp_deployment/` directory
❌ Using `config.settings.staging` without DB_PASSWORD
❌ Trying to add Cloud SQL config to staging.yaml
❌ Separating password into DB_PASSWORD env var
❌ Including `host` parameter in DATABASE_URL query string (causes psycopg2 conflicts)

✅ Deploy from project root
✅ Use `config.settings.wildebackyard_api` or ensure DB_PASSWORD is set for staging
✅ Password in DATABASE_URL (URL-encoded)
✅ GCS for media storage (direct client, not Django storage)
✅ Let settings file handle host configuration dynamically

## Verification After Deployment

```bash
# Check deployment succeeded
gcloud app versions list --service=wildebackyard-api --limit=1

# Test API
curl https://wildebackyard-api-dot-wildepod-339517.wl.r.appspot.com/api/docs/

# Check logs if broken
gcloud app logs read --service=wildebackyard-api --limit=20
```

## Emergency Rollback

```bash
# List versions
gcloud app versions list --service=wildebackyard-api

# Rollback to known working version
gcloud app services set-traffic wildebackyard-api --splits 20260203t104123=1
```
