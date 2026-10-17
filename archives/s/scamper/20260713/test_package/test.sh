#!/usr/bin/env bash
set -euo pipefail
"$1" -v 2>&1 | grep -i "scamper"
