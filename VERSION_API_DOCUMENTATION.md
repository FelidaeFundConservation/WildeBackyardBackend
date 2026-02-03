# Version Information API Endpoint

This document describes the version information API endpoint and the GitHub Actions workflow used to create releases with version information.

## API Endpoint

### GET /v1/info/version/

Returns the current version information for the deployed application, including the commit hash and release tag.

#### Request

```http
GET /v1/info/version/ HTTP/1.1
Host: your-api-domain.com
```

#### Response

**Status Code:** 200 OK

**Body:**
```json
{
  "commit_hash": "abc1234",
  "release_tag": "v1.0.0"
}
```

#### Authentication

This endpoint does not require authentication and is publicly accessible.

#### Example Usage

**Using curl:**
```bash
curl https://your-api-domain.com/v1/info/version/
```

**Using Python requests:**
```python
import requests

response = requests.get('https://your-api-domain.com/v1/info/version/')
version_info = response.json()
print(f"Commit: {version_info['commit_hash']}")
print(f"Version: {version_info['release_tag']}")
```

## Creating a Release

### Using GitHub Actions Workflow

The repository includes a GitHub Actions workflow (`create-release.yml`) that automates the process of creating releases with version information.

#### Steps to Create a Release:

1. Navigate to the **Actions** tab in your GitHub repository
2. Select the **"Create Release with Version Info"** workflow
3. Click **"Run workflow"**
4. Enter a version tag in the format `vX.Y.Z` (e.g., `v1.0.0`, `v2.1.3`)
5. Click **"Run workflow"** to start the process

#### What the Workflow Does:

1. **Validates the version tag format** - Ensures it follows semantic versioning (vX.Y.Z)
2. **Checks for duplicate tags** - Prevents creating releases with existing tags
3. **Creates and pushes a git tag** - Tags the current commit with the provided version
4. **Updates version.py** - Automatically updates the `config/version.py` file with:
   - The short commit hash of the tagged commit
   - The release tag
5. **Commits the version update** - Commits the updated version.py to the repository
6. **Creates a GitHub release** - Creates a release with automatically generated release notes
7. **Generates release notes** - Includes:
   - List of commits since the last release
   - Version information
   - API endpoint documentation

#### Version Tag Format

The version tag must follow semantic versioning format:
- **Format:** `vX.Y.Z` where X, Y, and Z are numbers
- **Examples:** 
  - ✅ `v1.0.0` - Valid
  - ✅ `v2.1.3` - Valid
  - ❌ `1.0.0` - Invalid (missing 'v' prefix)
  - ❌ `v1.0` - Invalid (incomplete version)

## Technical Details

### Version Storage

Version information is stored in `config/version.py`:

```python
VERSION = {
    "commit_hash": "abc1234",  # Short commit hash (7 characters)
    "release_tag": "v1.0.0",   # Semantic version tag
}
```

### Implementation

- **View:** `siteapps/info_views.py` - VersionInfoView
- **URL Pattern:** `v1/info/version/` defined in `config/urls.py`
- **Tests:** `siteapps/test_info_views.py`
- **Workflow:** `.github/workflows/create-release.yml`

### Default Values

When no release has been created yet, the endpoint returns:
```json
{
  "commit_hash": "unknown",
  "release_tag": "unknown"
}
```

## Best Practices

1. **Use semantic versioning** - Follow the vX.Y.Z format for all releases
2. **Create releases from stable branches** - Run the workflow from main or production branches
3. **Review generated release notes** - Check the automatically generated release notes for accuracy
4. **Deploy after tagging** - Deploy the tagged version to your environments

## Troubleshooting

### Tag Already Exists

If you see an error that the tag already exists:
1. Check existing tags with `git tag -l`
2. Delete the tag if needed: `git tag -d vX.Y.Z` and `git push origin :refs/tags/vX.Y.Z`
3. Try creating the release again with a new version number

### Invalid Tag Format

Ensure your tag follows the format `vX.Y.Z`:
- Must start with lowercase 'v'
- Must have exactly three numbers separated by dots
- No additional characters or suffixes

## Security Considerations

- The version endpoint is **publicly accessible** without authentication
- Only commit hashes and tags are exposed - no sensitive information
- The workflow requires repository write permissions
