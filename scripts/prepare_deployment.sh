#!/bin/bash
# Prepare deployment by updating version.py with current git commit info
# Usage: ./scripts/prepare_deployment.sh

set -e

# Get git information
SHORT_HASH=$(git rev-parse --short HEAD)
RELEASE_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "dev")
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "Preparing deployment..."
echo "  Commit: $SHORT_HASH"
echo "  Release: $RELEASE_TAG"
echo "  Branch: $BRANCH"

# Update config/version.py
cat > config/version.py << EOF
"""
Version information for the application.
This file is automatically updated by the deployment script.
"""

VERSION = {
    "commit_hash": "$SHORT_HASH",
    "release_tag": "$RELEASE_TAG",
    "branch": "$BRANCH",
}
EOF

echo "✓ Updated config/version.py"

# Export the short hash for use in deployment command
echo "SHORT_HASH=$SHORT_HASH"
