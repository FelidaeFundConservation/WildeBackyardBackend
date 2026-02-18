# Granting Secret Manager Permissions to GitHub Actions Service Account

This guide explains how to grant Secret Manager permissions to the GitHub Actions service account so that the `deploy-staging.yml` workflow can access database passwords stored in Google Secret Manager.

## Why This is Needed

The `deploy-staging.yml` workflow needs to run database migrations, which requires:
1. Access to the Cloud SQL database
2. The database password (stored in Google Secret Manager)
3. Permission to read secrets from Secret Manager

## Two Methods: Console UI or Command Line

Choose the method you prefer:

---

## Method 1: Google Cloud Console (UI)

### Step 1: Navigate to IAM & Admin

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: **wildepod-339517** (or your project ID)
3. In the left navigation menu, click **"IAM & Admin"** → **"IAM"**

### Step 2: Find the Service Account

1. In the IAM page, look for the service account used by GitHub Actions:
   - Service account name: `deploy-builds-github@wildepod-339517.iam.gserviceaccount.com`
   - Or the format: `deploy-builds-github@[PROJECT-ID].iam.gserviceaccount.com`
   
2. If you don't see it in the list:
   - Click the **"Include Google-provided role grants"** checkbox at the top
   - Or click **"+ GRANT ACCESS"** to add it (see Step 3)

### Step 3: Grant Secret Manager Access

**If the service account is already listed:**

1. Click the **pencil icon (Edit)** next to the service account
2. Click **"+ ADD ANOTHER ROLE"**
3. In the "Select a role" dropdown:
   - Type: `Secret Manager Secret Accessor`
   - Or navigate: **Secret Manager** → **Secret Manager Secret Accessor**
4. Click **"SAVE"**

**If the service account is NOT listed:**

1. Click the **"+ GRANT ACCESS"** button at the top
2. In the "New principals" field, enter:
   ```
   deploy-builds-github@wildepod-339517.iam.gserviceaccount.com
   ```
   (Replace `wildepod-339517` with your actual project ID)
3. Click the "Select a role" dropdown:
   - Type: `Secret Manager Secret Accessor`
   - Or navigate: **Secret Manager** → **Secret Manager Secret Accessor**
4. Click **"SAVE"**

### Step 4: Verify the Permission

1. The service account should now appear in the IAM list
2. Look for the role: **Secret Manager Secret Accessor**
3. You should see it listed under the service account's roles

### Visual Guide for Console Navigation

```
Google Cloud Console
└── Project: wildepod-339517
    └── Navigation Menu (≡)
        └── IAM & Admin
            └── IAM
                └── Find: deploy-builds-github@...
                    └── Edit (pencil icon)
                        └── Add Another Role
                            └── Select: Secret Manager Secret Accessor
                                └── Save
```

---

## Method 2: Command Line (gcloud CLI)

If you prefer using the command line:

```bash
# Grant Secret Manager Secret Accessor role
gcloud projects add-iam-policy-binding wildepod-339517 \
  --member="serviceAccount:deploy-builds-github@wildepod-339517.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Verify the permission was granted:

```bash
# List all IAM bindings for the service account
gcloud projects get-iam-policy wildepod-339517 \
  --flatten="bindings[].members" \
  --filter="bindings.members:deploy-builds-github@wildepod-339517.iam.gserviceaccount.com" \
  --format="table(bindings.role)"
```

You should see `roles/secretmanager.secretAccessor` in the output.

---

## What This Permission Allows

The **Secret Manager Secret Accessor** role allows the service account to:
- ✅ Read secret values from Secret Manager
- ✅ Access secret versions
- ❌ Cannot create, update, or delete secrets (read-only)

This is the **minimum permission** needed for the workflow to retrieve database passwords.

---

## Testing the Workflow After Granting Permission

1. Go to your GitHub repository
2. Navigate to **Actions** tab
3. Select **"Deploy to GCP Staging"** workflow
4. Click **"Run workflow"**
5. Select the branch and click **"Run workflow"**
6. The **"Database Migrations"** job should now succeed

---

## Troubleshooting

### Error: "Permission 'secretmanager.versions.access' denied"

**Cause:** The service account doesn't have Secret Manager permissions yet.

**Solution:** Follow Method 1 or Method 2 above to grant the permission.

### Error: "Secret not found: staging_db_password"

**Cause:** The secret doesn't exist in Secret Manager.

**Solution:** Create the secret in Secret Manager:

**Via Console:**
1. Go to **Security** → **Secret Manager**
2. Click **"+ CREATE SECRET"**
3. Name: `staging_db_password`
4. Secret value: Enter your database password
5. Click **"CREATE SECRET"**

**Via Command Line:**
```bash
echo -n "YOUR_DATABASE_PASSWORD" | \
  gcloud secrets create staging_db_password \
    --data-file=- \
    --replication-policy="automatic" \
    --project=wildepod-339517
```

### Error: "Service account not found"

**Cause:** The service account might have a different name.

**Solution:** Check the actual service account name:

1. In Cloud Console, go to **IAM & Admin** → **Service Accounts**
2. Look for the GitHub Actions service account
3. Use the exact email address shown

---

## Alternative: Using GitHub Secrets Instead

If you prefer not to use Google Secret Manager, you can use GitHub Secrets instead:

1. Store the database password in GitHub Secrets as `WILDEBACKYARD_API_DB_PASSWORD`
2. Update the workflow to use `${{ secrets.WILDEBACKYARD_API_DB_PASSWORD }}`
3. No GCP permissions needed

**Trade-offs:**
- ✅ Simpler setup (no GCP permission changes)
- ❌ Less secure (password stored outside GCP)
- ❌ Password in multiple places (harder to rotate)
- ❌ Doesn't follow GCP best practices

**Recommendation:** Use Google Secret Manager for production deployments.

---

## Complete IAM Roles for GitHub Actions

For reference, the complete set of roles needed for the GitHub Actions service account:

| Role | Purpose |
|------|---------|
| `roles/appengine.appAdmin` | Deploy to App Engine |
| `roles/cloudbuild.builds.editor` | Build container images |
| `roles/cloudsql.client` | Connect to Cloud SQL |
| `roles/secretmanager.secretAccessor` | Read secrets from Secret Manager |
| `roles/storage.admin` | Manage Cloud Storage buckets |
| `roles/iam.serviceAccountUser` | Act as service account |

All of these can be granted via the same UI process described in Method 1.

---

## Security Best Practices

1. **Use Secret Manager** for sensitive data like database passwords
2. **Principle of Least Privilege**: Only grant `secretAccessor` role (read-only)
3. **Audit Access**: Regularly review who has access to secrets
4. **Rotate Credentials**: Change database passwords periodically
5. **Delete Old Keys**: Remove unused service account keys

---

## Need Help?

- [Google Cloud IAM Documentation](https://cloud.google.com/iam/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Service Accounts Overview](https://cloud.google.com/iam/docs/service-accounts)
