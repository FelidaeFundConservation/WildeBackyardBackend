# Pre-Deployment Checklist

## CRITICAL: Always run these checks before deploying

### 1. Verify Configuration Files
```bash
# Check entrypoint is correct in yaml files
grep "entrypoint:" gcp_deployment/staging.yaml
# Should output: entrypoint: gunicorn -t 2400 -b :$PORT config.wsgi.staging:application

grep "entrypoint:" gcp_deployment/prod.yaml
# Should output: entrypoint: gunicorn -t 2400 -b :$PORT config.wsgi.prod:application
```

### 2. Use Deployment Scripts (RECOMMENDED)
**DO NOT manually run `gcloud app deploy`**

Use the provided deployment scripts:
```bash
# For staging
cd gcp_deployment/scripts
./deploy_staging.sh

# For production
./deploy_prod.sh
```

These scripts validate configuration before deploying.

### 3. Test Locally First
```bash
# Activate environment
source .venv/bin/activate

# Test with staging settings
uv run manage.py check --settings=config.settings.staging

# Test WSGI application loads
python -c "from config.wsgi.staging import application; print('WSGI OK')"
```

### 4. After Deployment - Verify
```bash
# Check backend is responding
curl https://wildebackyard-api-dot-wildepod-339517.wl.r.appspot.com/api/schema/

# Check logs for errors
gcloud app logs read -s wildebackyard-api --limit 50 | grep -E "(ERROR|500|gunicorn: not found)"
```

## Common Issues to Avoid

### ❌ WRONG: Direct gcloud commands without validation
```bash
cd gcp_deployment
gcloud app deploy staging.yaml --quiet  # NO VALIDATION!
```

### ✅ RIGHT: Use deployment scripts
```bash
cd gcp_deployment/scripts
./deploy_staging.sh  # Validates config, then deploys
```

### ❌ WRONG: Using python instead of uv
```bash
python manage.py runserver  # Wrong on this project
```

### ✅ RIGHT: Always use uv
```bash
uv run manage.py runserver --settings=config.settings.local
```

### ❌ WRONG: Wrong entrypoint format
```yaml
entrypoint: gunicorn -t 2400 -b :$PORT staging:app
```

### ✅ RIGHT: Correct Django WSGI path
```yaml
entrypoint: gunicorn -t 2400 -b :$PORT config.wsgi.staging:application
```

## Rollback Procedure

If deployment fails:
```bash
# List recent versions
gcloud app versions list --service=wildebackyard-api

# Rollback to working version
gcloud app services set-traffic wildebackyard-api --splits 20260203t104123=1
```

## Emergency Contacts

- Logs: `gcloud app logs tail -s wildebackyard-api`
- Status: https://console.cloud.google.com/appengine
- Project: wildepod-339517
