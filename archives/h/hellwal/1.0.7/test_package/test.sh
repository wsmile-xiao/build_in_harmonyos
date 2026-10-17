#!/data/service/hnp/bin/bash
set -euo pipefail

echo "[step] L2: hellwal smoke test (--version)"
hellwal --version && echo "        [ok] hellwal --version passed" || {
    echo "[step] Retrying with --help..."
    hellwal --help > /dev/null 2>&1 && echo "        [ok] hellwal --help passed" || {
        echo "        [fail] hellwal failed both --version and --help"
        exit 1
    }
}
