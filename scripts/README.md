# Deployment Scripts

This directory contains scripts for deploying the WildeBackyard Backend API to Google Cloud Platform.

## Scripts

### `prepare_deployment.sh`

Prepares the deployment by updating `config/version.py` with current git commit information.

**Usage:**
```bash
./scripts/prepare_deployment.sh
```

**What it does:**
- Gets current git commit short SHA
- Gets git tag (or "dev" if no tag)
- Gets current branch name
- Updates `config/version.py` with version information
- Outputs SHORT_HASH for use in deployment commands

**Output:**
```python
# config/version.py
VERSION = {
    "commit_hash": "e7373b6",
    "release_tag": "v1.0.0",  # or "dev" if no tag
    "branch": "main",
}
```

### `deploy_gcp.sh`

Comprehensive deployment script that handles version updates, static file collection, and GCP deployment.

**Usage:**
```bash
# Deploy without routing traffic (recommended for testing)
./scripts/deploy_gcp.sh --config app.yaml

# Deploy and immediately route traffic
./scripts/deploy_gcp.sh --config app.yaml --promote

# Deploy staging configuration
./scripts/deploy_gcp.sh --config staging.yaml --promote
```

**Options:**
- `--promote` - Route traffic to the new version immediately (default: no traffic routing)
- `--config FILE` - Config file to deploy (default: `app.yaml`)

**What it does:**
1. Runs `prepare_deployment.sh` to update version info
2. Gets git short SHA for versioning (e.g., `e7373b6`)
3. Warns if there are uncommitted changes
4. Collects static files with appropriate settings
5. Deploys to GCP with git SHA as version name
6. Displays deployment info and helpful commands

**Version Format:**
- Uses git short SHA as version: `e7373b6`
- Version URL: `https://e7373b6-dot-wildebackyard-api-dot-wildepod-339517.wl.r.appspot.com`
- Traceable back to git commit

## Why Git SHA Versions?

**Benefits over timestamp versions:**
1. **Traceability**: Version name directly maps to git commit
2. **Reproducibility**: Can checkout exact code that's deployed
3. **Debugging**: Easy to compare deployed code with local changes
4. **Consistency**: Matches GitHub Actions workflow behavior
5. **Human-readable**: Shorter than timestamp (7 chars vs 15)

**Example:**
- Timestamp version: `20260214t132536` (what's in this?)
- Git SHA version: `e7373b6` (git show e7373b6 to see what's deployed)

## Version Information API

The version information is available at runtime:

```python
from config.version import VERSION

print(VERSION["commit_hash"])  # "e7373b6"
print(VERSION["release_tag"])  # "v1.0.0" or "dev"
print(VERSION["branch"])       # "main"
```

You can expose this via an API endpoint:

```python
# siteapps/users/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from config.version import VERSION

@api_view(['GET'])
def version_info(request):
    return Response(VERSION)
```

## Comparison with GitHub Actions Workflow

The manual deployment scripts mimic the GitHub Actions workflow behavior:

| Feature | GitHub Actions | Manual Scripts | Old Manual |
|---------|---------------|----------------|------------|
| Version format | Git SHA | Git SHA | Timestamp |
| Updates version.py | ✅ | ✅ | ❌ |
| Traceable to commit | ✅ | ✅ | ❌ |
| Uncommitted warning | ❌ | ✅ | ❌ |
| No-promote option | ✅ | ✅ | Manual flag |

## Best Practices

1. **Always commit before deploying**: Version matches code exactly
2. **Test before promoting**: Deploy with `--no-promote`, test version URL, then route traffic
3. **Tag releases**: Use git tags for production deployments
4. **Check version.py**: Committed version.py shows last manual deployment

## Troubleshooting

**Q: Version already exists?**
```bash
# This means the commit SHA is already deployed
# Either use a new commit, or delete the old version:
gcloud app versions delete e7373b6 --service=wildebackyard-api
```

**Q: Uncommitted changes warning?**
```bash
# Commit your changes first:
git add .
git commit -m "Your changes"

# Or force deploy (not recommended):
# The script will prompt you to continue
```

**Q: Want to use timestamp version?**
```bash
# Use manual gcloud command:
gcloud app deploy app.yaml --version="$(date +%Y%m%dt%H%M%S)" --quiet
```
