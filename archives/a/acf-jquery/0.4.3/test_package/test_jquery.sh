#!/bin/bash
# Verify the packaged ACF jquery assets are installed.
# Usage: test_jquery.sh <pkg_folder>
set -euo pipefail

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

APPDIR="$PKG_FOLDER/share/acf/app"
STATICDIR="$PKG_FOLDER/share/acf/www/skins/static"

if [ ! -d "$APPDIR" ]; then
    echo "ERROR: ACF app dir not found: $APPDIR"
    exit 1
fi

# Core jquery libs (APP_DIST *.js)
REQUIRED_JS=(
    jquery-latest.js
    jquery.flot.js
    jquery.flot.time.js
    jquery.tablesorter.js
    jquery.tablesorter.widgets.js
    excanvas.js
)

for name in "${REQUIRED_JS[@]}"; do
    f="$APPDIR/$name"
    if [ ! -f "$f" ]; then
        echo "ERROR: required js file missing: $f"
        exit 1
    fi
    echo "  [ok] $name"
done

# Subdirs (APP_DIST widgets/*.js parsers/*.js)
for sub in widgets parsers; do
    d="$APPDIR/$sub"
    if [ ! -d "$d" ]; then
        echo "ERROR: required subdir missing: $d"
        exit 1
    fi
    count=$(find "$d" -maxdepth 1 -name '*.js' | wc -l)
    if [ "$count" -eq 0 ]; then
        echo "ERROR: no js files in $d"
        exit 1
    fi
    echo "  [ok] $sub/ ($count js files)"
done

# STATIC_DIST tablesorter theme assets
tsdir="$STATICDIR/tablesorter"
if [ ! -d "$tsdir" ]; then
    echo "ERROR: tablesorter theme dir not found: $tsdir"
    exit 1
fi
count=$(find "$tsdir" -maxdepth 1 \( -name '*.css' -o -name '*.png' \) | wc -l)
if [ "$count" -eq 0 ]; then
    echo "ERROR: no css/png assets in $tsdir"
    exit 1
fi
echo "  [ok] tablesorter/ ($count css/png assets)"

echo "=== Results: 9 passed, 0 failed ==="
exit 0
