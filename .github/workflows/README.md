# GitHub Actions Workflows

## Reusable Workflows

### build-test-coverage.yml

This is a **reusable workflow** that performs building, testing, and code coverage checks. It can be called from other workflows to avoid code duplication.

#### Features

- Python environment setup
- Install GDAL and spatial libraries
- Install project dependencies
- Run linting with flake8
- Run security checks with bandit
- Check for hardcoded secrets
- Run pytest tests
- Upload test results and coverage reports
- Comment coverage on pull requests
- Enforce coverage threshold (70%)

#### Usage

To use this reusable workflow in another workflow, add it as a job:

```yaml
jobs:
  test:
    uses: ./.github/workflows/build-test-coverage.yml
    with:
      branch: ${{ github.ref }}           # Optional: branch or commit SHA to test
      skip_tests: false                    # Optional: skip test execution
    secrets: inherit                       # Required: pass all secrets to reusable workflow
```

#### Inputs

| Input | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `branch` | string | No | `''` | Branch or commit SHA to test. Defaults to the triggering ref. |
| `skip_tests` | boolean | No | `false` | Whether to skip test execution. |

#### Secrets

The workflow requires access to repository secrets. Use `secrets: inherit` to pass all secrets to the reusable workflow.

Required secrets:
- `GCP_PROJECT_ID` - Google Cloud Project ID
- `WEBSITE_HOSTNAME` - Website hostname for testing

## deploy-staging.yml

This workflow deploys the application to Google Cloud Platform App Engine (staging environment).

### Trigger

- **Manual only** via workflow_dispatch
- Allows specifying branch and whether to skip tests

### Required GitHub Secrets

| Secret | Description | Example/Notes |
|--------|-------------|---------------|
| `GCP_SA_KEY` | Service account JSON key for GCP authentication | Full JSON key file content |
| `GCP_PROJECT_ID` | Google Cloud Project ID | `wildepod-339517` |
| `DJANGO_SECRET_KEY` | Django secret key for settings | Random 50+ character string |
| `WILDEBACKYARD_API_DB_PASSWORD` | Database password (URL-decoded) | `/REDACTED=` |
| `DJANGO_SUPERUSER_PASSWORD` | Admin user password for initial setup | Strong password |
| `WEBSITE_HOSTNAME` | Website hostname | Used in settings |

**Important Notes:**
- `WILDEBACKYARD_API_DB_PASSWORD` should be the URL-decoded password (not URL-encoded)
- The workflow will URL-encode it automatically when constructing the database URL
- This password must match the password in `app.yaml`'s `WILDEBACKYARD_API_DATABASE_URL`

**Alternative: Using Google Secret Manager (Recommended for Production)**

For better security, you can use Google Secret Manager instead of GitHub Secrets:
- Store the database password in Google Secret Manager as `staging_db_password`
- Grant the service account `roles/secretmanager.secretAccessor` permission
- See detailed instructions: [gcp_deployment/GRANT_SECRET_MANAGER_PERMISSIONS.md](../../gcp_deployment/GRANT_SECRET_MANAGER_PERMISSIONS.md)
- Benefits: Centralized secret management, better audit trail, easier credential rotation

### Workflow Jobs

1. **test**: Runs the reusable build-test-coverage workflow
2. **build**: Validates GCP credentials, app.yaml, and Cloud SQL instance
3. **deploy**: Deploys to App Engine with no-promote flag
4. **migrate**: Runs database migrations using Cloud SQL Proxy
5. **smoke-test**: Health checks and promotes version if successful
6. **notify**: Sends deployment status notification

#### Standalone Usage

This workflow can also run standalone on:
- Push to `main` branch
- Pull requests
- Manual workflow dispatch

## Example: deploy-staging-example.yml

The `deploy-staging-example.yml` workflow demonstrates how to use the reusable `build-test-coverage.yml` workflow:

```yaml
jobs:
  # Use the reusable test workflow
  test:
    uses: ./.github/workflows/build-test-coverage.yml
    with:
      branch: ${{ github.event.inputs.branch || github.ref }}
      skip_tests: ${{ github.event.inputs.skip_tests == 'true' }}
    secrets: inherit

  # Build job depends on test completion
  build:
    name: Build Validation
    runs-on: ubuntu-latest
    needs: test
    # ... build steps ...

  # Deploy job depends on both test and build
  deploy:
    name: Deploy to App Engine
    runs-on: ubuntu-latest
    needs: [test, build]
    # ... deployment steps ...
```

## Benefits of Reusable Workflows

1. **DRY Principle**: Write once, use many times
2. **Consistency**: Same test process across all workflows
3. **Maintainability**: Update tests in one place
4. **Modularity**: Compose complex workflows from simple, reusable pieces

## References

- [GitHub Actions: Reusing Workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [GitHub Actions: Workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
