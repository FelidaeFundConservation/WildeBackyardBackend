# GCP Deployment Reference - ACTUAL WORKING CONFIGURATION

**Last verified working:** Version 20260203t104123

## CRITICAL: Always Check Working Version First

Before deploying, check what the last working version actually used:
```bash
gcloud app versions describe 20260203t104123 --service=wildebackyard-api --format=yaml
```

## Correct Deployment Process

### Recommended: Use Deployment Script (with Git SHA versioning)

```bash
cd /home/jnovak/Projects/WildeBackyardBackend

# Deploy without routing traffic (for testing)
./scripts/deploy_gcp.sh --config app.yaml

# Deploy and route traffic immediately
./scripts/deploy_gcp.sh --config app.yaml --promote

# Deploy staging configuration
./scripts/deploy_gcp.sh --config staging.yaml
```

**Benefits:**
- Automatically updates `config/version.py` with commit hash
- Uses git short SHA as GCP version (e.g., `e7373b6` instead of `20260214t132536`)
- Version is traceable to git commit
- Warns about uncommitted changes
- Provides deployment URLs and commands

### Manual Deployment (legacy method)

```bash
cd /home/jnovak/Projects/WildeBackyardBackend  # PROJECT ROOT, not gcp_deployment/

# 1. Update version.py (optional but recommended)
./scripts/prepare_deployment.sh
SHORT_HASH=$(git rev-parse --short HEAD)

# 2. Collect static files
WILDEBACKYARD_API_DATABASE_URL="postgres://dummy:dummy@localhost/dummy" \
  uv run python manage.py collectstatic --settings=config.settings.wildebackyard_api --noinput

# 3. Deploy with git SHA version
gcloud app deploy app.yaml --version="$SHORT_HASH" --no-promote --quiet

# 4. Route traffic once tested
gcloud app services set-traffic wildebackyard-api --splits "$SHORT_HASH=1"
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
❌ Using `config.settings.staging` without setting DB_PASSWORD environment variable
❌ Trying to add Cloud SQL config to staging.yaml
❌ Including `host` parameter in DATABASE_URL query string (causes psycopg2 conflicts)

✅ Deploy from project root
✅ Use `config.settings.wildebackyard_api` (with DATABASE_URL) OR use `config.settings.staging` (with DB_PASSWORD)
✅ Password in DATABASE_URL (URL-encoded) for wildebackyard_api settings
✅ Password in DB_PASSWORD for staging settings
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
