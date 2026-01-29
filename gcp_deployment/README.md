# WildeBackyardBackend GCP Deployment

This directory contains all the files and scripts needed to deploy the WildeBackyardBackend Django application to Google Cloud Platform (GCP) App Engine.

## Quick Start

### First-time Setup

1. **Install Google Cloud SDK**
   ```bash
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   ```

2. **Set your GCP project**
   ```bash
   export GCP_PROJECT_ID="your-project-id"
   gcloud config set project $GCP_PROJECT_ID
   ```

3. **Deploy to staging environment**
   ```bash
   cd /home/jnovak/Projects/WildeBackyardBackend
   ./gcp_deployment/scripts/deploy_gcp.sh staging --full
   ```

### Standard Deployment

```bash
# Deploy to staging
./gcp_deployment/scripts/deploy_gcp.sh staging --deploy-only

# Deploy to production
./gcp_deployment/scripts/deploy_gcp.sh prod --deploy-only
```

### Custom Development Environment

```bash
# Create personal dev environment
./gcp_deployment/scripts/deploy_custom.sh your-name-dev --use-existing-db --db-instance your-db-instance --full
./gcp_deployment/scripts/post_deploy_setup.sh your-name-dev
```

## Directory Structure

```
gcp_deployment/
├── scripts/              # Deployment automation scripts
│   ├── deploy_gcp.sh            # Main deployment script
│   ├── deploy_custom.sh         # Create custom environments
│   ├── deploy_manager.sh        # Environment management
│   ├── pre_deploy_check.sh      # Pre-deployment validation
│   └── post_deploy_setup.sh     # Post-deployment configuration
├── templates/            # Configuration templates
│   ├── .env.local.example       # Environment variables template
│   ├── deploy.config.example    # Deployment config template
│   ├── TEMPLATE_app_yaml.yaml   # App Engine config template
│   ├── TEMPLATE_config_settings.py  # Django settings template
│   ├── TEMPLATE_config_wsgi.py      # WSGI config template
│   └── TEMPLATE_entry_point.py      # Entry point template
├── staging.yaml          # App Engine config for staging
├── prod.yaml             # App Engine config for production
├── dispatch.yaml         # URL routing configuration
├── DEPLOYMENT_GUIDE.md   # Comprehensive deployment guide
├── QUICK_REFERENCE.md    # Quick command reference
└── GCP_SETUP_INSTRUCTIONS.md  # Initial GCP setup
```

## Key Files in Project Root

- `.gcloudignore` - Files to exclude from GCP deployment
- `staging.py` - WSGI entry point for staging
- `prod.py` - WSGI entry point for production

## Deployment Scripts

### deploy_gcp.sh
Main deployment script with options:
- `--setup-db` - Create new Cloud SQL database
- `--use-existing-db` - Use existing database
- `--migrate-db` - Run migrations only
- `--deploy-only` - Deploy app without DB operations
- `--full` - Complete setup (DB + deployment)
- `--dry-run` - Preview changes without deploying

### deploy_custom.sh
Create custom development environments:
```bash
./gcp_deployment/scripts/deploy_custom.sh myname-dev --use-existing-db --db-instance wildepoddb --full
```

### pre_deploy_check.sh
Validates code before deployment:
- Runs tests
- Checks configuration
- Validates environment variables
- Ensures no sensitive data in code

### post_deploy_setup.sh
Completes setup after deployment:
- Runs database migrations
- Collects static files
- Creates superuser (optional)
- Tests deployment

## Environment Configuration

### Required Environment Variables

Create `.env.<environment>` files (e.g., `.env.staging`, `.env.prod`) with:

```bash
# Django settings
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_SETTINGS_MODULE=config.settings.staging

# Database
PROD_DATABASE_URL=postgres://user:pass@/dbname?host=/cloudsql/project:region:instance

# Email
MAILGUN_SMTP_SERVER=smtp.mailgun.org
MAILGUN_SMTP_PORT=587
MAILGUN_SMTP_LOGIN=postmaster@your-domain.com
MAILGUN_SMTP_PASSWORD=your-password

# Cloud Storage
GS_BUCKET_NAME=your-bucket-name

# Mapbox (if using)
MAPBOX_ACCESS_TOKEN=your-token
```

### App Engine Configuration

Edit `gcp_deployment/staging.yaml` or `gcp_deployment/prod.yaml`:

```yaml
runtime: python310
instance_class: F2
entrypoint: gunicorn -t 2400 -b :$PORT staging:app

env_variables:
  DJANGO_SETTINGS_MODULE: "config.settings.staging"
  PYTHON_ENV: "production"

automatic_scaling:
  min_idle_instances: 0
  max_idle_instances: 2
  max_concurrent_requests: 50
```

## GitHub Actions CI/CD

Automated deployment workflow is in `.github/workflows/deploy-staging-example.yml`.

To set up:

1. Add GCP service account key to GitHub secrets:
   ```bash
   # Create service account
   gcloud iam service-accounts create github-actions --display-name="GitHub Actions"

   # Grant permissions
   gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
     --member="serviceAccount:github-actions@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/appengine.appAdmin"

   # Create key
   gcloud iam service-accounts keys create key.json \
     --iam-account=github-actions@$GCP_PROJECT_ID.iam.gserviceaccount.com
   ```

2. Add `key.json` content to GitHub repository secret `GCP_SA_KEY`

3. Push to staging/prod branch to trigger automatic deployment

## Database Setup

### Create Cloud SQL Instance

```bash
gcloud sql instances create wildepoddb \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1
```

### Create Database and User

```bash
gcloud sql databases create wildebackyard_staging --instance=wildepoddb
gcloud sql users create staging_user --instance=wildepoddb --password=secure-password
```

### Connect Locally via Cloud SQL Proxy

```bash
cloud-sql-proxy --port 5440 project-id:region:instance-name
```

## Common Commands

### Deploy staging
```bash
./gcp_deployment/scripts/deploy_gcp.sh staging --deploy-only
```

### Deploy production
```bash
./gcp_deployment/scripts/deploy_gcp.sh prod --full
```

### Run migrations only
```bash
./gcp_deployment/scripts/deploy_gcp.sh staging --migrate-db
```

### Check logs
```bash
gcloud app logs tail -s default
gcloud app logs tail -s staging
```

### SSH to instance
```bash
gcloud app instances ssh --service=staging --version=latest
```

## Troubleshooting

### View deployment logs
```bash
gcloud app logs tail
```

### Check service status
```bash
gcloud app services list
gcloud app versions list
```

### Rollback deployment
```bash
gcloud app versions list
gcloud app services set-traffic default --splits=PREVIOUS_VERSION=1
```

### Database connection issues
```bash
# Test connection via Cloud SQL Proxy
cloud-sql-proxy project:region:instance
psql -h 127.0.0.1 -U username -d database_name
```

## Security Notes

- Never commit `.env.*` files (except `.env.*.example`)
- Use Secret Manager for sensitive credentials
- Rotate database passwords regularly
- Enable Cloud SQL SSL connections in production
- Use least-privilege IAM roles

## Resources

- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Comprehensive deployment guide
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Quick command reference
- [GCP_SETUP_INSTRUCTIONS.md](./GCP_SETUP_INSTRUCTIONS.md) - Initial GCP setup
- [Google Cloud App Engine Docs](https://cloud.google.com/appengine/docs)
- [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)

## Support

For issues or questions about deployment, check:
1. Deployment logs: `gcloud app logs tail`
2. Cloud Console: https://console.cloud.google.com/
3. Service status: `gcloud app services list`
