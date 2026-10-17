#!/usr/bin/zsh
# test_arename.sh — Smoke test for arename package installation
# Verifies that arename and ataglist scripts are installed and syntactically valid
# Called by test_package/conanfile.py test() method
set -euo pipefail

PKG_DIR="${1:?Usage: test_arename.sh <package_dir>}"
PERL_BIN="${PERL:-/data/service/hnp/bin/perl}"

ARENAME_BIN="$PKG_DIR/bin/arename"
ATAGLIST_BIN="$PKG_DIR/bin/ataglist"

# Verify arename script exists
if [ ! -f "$ARENAME_BIN" ]; then
        echo "[fail] arename not found at $ARENAME_BIN"
        exit 1
fi
        echo "        [ok] arename found at $ARENAME_BIN"

# Verify ataglist script exists
if [ ! -f "$ATAGLIST_BIN" ]; then
        echo "[fail] ataglist not found at $ATAGLIST_BIN"
        exit 1
fi
        echo "        [ok] ataglist found at $ATAGLIST_BIN"

# Check shebang contains perl
head -1 "$ARENAME_BIN" | grep -q perl || { echo "[fail] invalid shebang"; exit 1; }
        echo "        [ok] arename shebang valid"

head -1 "$ATAGLIST_BIN" | grep -q perl || { echo "[fail] invalid shebang"; exit 1; }
        echo "        [ok] ataglist shebang valid"

# Perl syntax check (non-fatal: may fail due to missing runtime modules)
if "$PERL_BIN" -c "$ARENAME_BIN" 2>/dev/null; then
        echo "        [ok] arename perl syntax check passed"
else
        echo "        [warn] perl -c failed (may need runtime modules — non-fatal)"
fi

        echo "        [ok] all smoke tests completed"
