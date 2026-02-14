#!/bin/bash
# Deploy to GCP App Engine with git SHA versioning
# Usage: ./scripts/deploy_gcp.sh [--promote] [--config app.yaml|staging.yaml]

set -e

PROMOTE=""
CONFIG_FILE="app.yaml"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --promote)
      PROMOTE="--promote"
      shift
      ;;
    --config)
      CONFIG_FILE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--promote] [--config app.yaml|staging.yaml]"
      exit 1
      ;;
  esac
done

# Prepare version.py
echo "==> Preparing deployment..."
./scripts/prepare_deployment.sh

# Get the short hash for versioning
SHORT_HASH=$(git rev-parse --short HEAD)

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
  echo "⚠️  Warning: You have uncommitted changes"
  echo "   Version $SHORT_HASH won't match your local changes"
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Collect static files (with dummy DB URL for wildebackyard_api settings)
echo "==> Collecting static files..."
if [[ "$CONFIG_FILE" == "app.yaml" ]]; then
  WILDEBACKYARD_API_DATABASE_URL="postgres://dummy:dummy@localhost/dummy" \
    uv run python manage.py collectstatic --settings=config.settings.wildebackyard_api --noinput
else
  uv run python manage.py collectstatic --settings=config.settings.staging --noinput
fi

# Deploy to GCP
echo "==> Deploying to GCP..."
echo "   Config: $CONFIG_FILE"
echo "   Version: $SHORT_HASH"
if [[ -n "$PROMOTE" ]]; then
  echo "   Traffic: Will route traffic to this version"
else
  echo "   Traffic: No traffic routing (use --promote to route traffic)"
fi

if [[ -z "$PROMOTE" ]]; then
  NO_PROMOTE="--no-promote"
fi

gcloud app deploy "$CONFIG_FILE" \
  --version="$SHORT_HASH" \
  $NO_PROMOTE \
  --quiet

# Get service name from config file
SERVICE=$(grep "^service:" "$CONFIG_FILE" | awk '{print $2}')

# Display deployment info
echo ""
echo "✓ Deployment complete!"
echo ""
echo "Version URL: https://$SHORT_HASH-dot-$SERVICE-dot-wildepod-339517.wl.r.appspot.com"
echo ""
if [[ -z "$PROMOTE" ]]; then
  echo "To route traffic to this version:"
  echo "  gcloud app services set-traffic $SERVICE --splits $SHORT_HASH=1"
fi
echo ""
echo "To view logs:"
echo "  gcloud app logs tail -s $SERVICE --version=$SHORT_HASH"
