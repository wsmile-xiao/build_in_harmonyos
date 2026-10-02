#!/usr/bin/env bash
# Run the actual PHP API assertions against the packaged module.
set -euo pipefail
php="$1"
module="$2"
"$php" -n -d "extension=$module" "$(dirname "$0")/test_enchant.php"
