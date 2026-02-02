# GCP Service Account Setup for GitHub Actions

## Steps to enable GitHub Actions deployment:

1. Create a service account for GitHub Actions:
```bash
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions Deployment" \
    --project=wildepod-339517
```

2. Grant necessary permissions:
```bash
# App Engine deployment
gcloud projects add-iam-policy-binding wildepod-339517 \
    --member="serviceAccount:github-actions@wildepod-339517.iam.gserviceaccount.com" \
    --role="roles/appengine.appAdmin"

# Cloud Build
gcloud projects add-iam-policy-binding wildepod-339517 \
    --member="serviceAccount:github-actions@wildepod-339517.iam.gserviceaccount.com" \
    --role="roles/cloudbuild.builds.editor"

# Cloud SQL
gcloud projects add-iam-policy-binding wildepod-339517 \
    --member="serviceAccount:github-actions@wildepod-339517.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

# Secret Manager
gcloud projects add-iam-policy-binding wildepod-339517 \
    --member="serviceAccount:github-actions@wildepod-339517.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Storage Admin (for static files)
gcloud projects add-iam-policy-binding wildepod-339517 \
    --member="serviceAccount:github-actions@wildepod-339517.iam.gserviceaccount.com" \
    --role="roles/storage.admin"
```

3. Create and download service account key:
```bash
gcloud iam service-accounts keys create github-sa-key.json \
    --iam-account=github-actions@wildepod-339517.iam.gserviceaccount.com
```

4. Add the key to GitHub Secrets:
   - Go to your repository on GitHub
   - Navigate to Settings > Secrets and variables > Actions
   - Click "New repository secret"
   - Name: `GCP_SA_KEY`
   - Value: Paste the entire contents of `github-sa-key.json`

5. Delete the local key file for security:
```bash
rm github-sa-key.json
```

## Additional Secrets to Add to GitHub:

Add these secrets to your GitHub repository for the deployment to work:

- `GCP_SA_KEY`: Service account key (from above)
- Additional environment variables as needed

## Testing the Workflow:

After setup, push to the jnovak-dev branch to trigger automatic deployment.
