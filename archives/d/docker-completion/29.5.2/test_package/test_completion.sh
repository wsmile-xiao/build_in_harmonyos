#!/bin/bash
set -euo pipefail

COMPLETION_FILE="$1"

# Check file exists
test -f "$COMPLETION_FILE"

# Check it's a valid bash script (syntax check)
bash -n "$COMPLETION_FILE"

# Check it has docker completion content (functions starting with __docker)
grep -q '__docker' "$COMPLETION_FILE"

echo "PASS: docker-completion test passed"
