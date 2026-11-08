#!/usr/bin/env sh
# Usage: ci/deploy.sh <staging|production>   (run by GitLab CI only)
set -eu
echo "Deploying to $1"
