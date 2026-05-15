#!/usr/bin/env bash
set -euo pipefail

VERSION=$(git describe --tags --always 2>/dev/null || git rev-parse --short HEAD)
OUTPUT="nestsshare-${VERSION}.zip"

git archive --format=zip --prefix=nestsshare/ HEAD -o "$OUTPUT"

echo "Gerado: $OUTPUT"
