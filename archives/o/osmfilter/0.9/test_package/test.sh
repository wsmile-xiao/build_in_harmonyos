#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for osmfilter executable
set -euo pipefail

# Conan's VirtualRunEnv puts binaries in PATH via env="conanrun"
OSMFILTER_BIN="osmfilter"
OSMCONVERT_BIN="osmconvert"

# Temp directory with trap cleanup
TMPDIR_TEST="$HOME/tmp/osmfilter-test-$$"
mkdir -p "$TMPDIR_TEST"
trap 'rm -rf "$TMPDIR_TEST"' EXIT

# --- Test 1: osmfilter --help (version check) ---
echo "[test] osmfilter --help"
if "${OSMFILTER_BIN}" --help 2>&1 | grep -q "osmfilter"; then
    echo "  PASS: osmfilter --help OK"
else
    echo "  FAIL: osmfilter --help failed"
    exit 1
fi

# --- Test 2: osmfilter tag filtering (drop amenity tags) ---
echo "[test] osmfilter --drop-tags=amenity"
cat > "$TMPDIR_TEST/test.osm" << 'OSMEOF'
<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
  <node id="1" lat="52.5" lon="13.4">
    <tag k="amenity" v="cafe"/>
    <tag k="name" v="Test Cafe"/>
  </node>
  <node id="2" lat="52.5" lon="13.5">
    <tag k="highway" v="bus_stop"/>
  </node>
</osm>
OSMEOF

"${OSMFILTER_BIN}" "$TMPDIR_TEST/test.osm" --drop-tags="amenity" -o="$TMPDIR_TEST/out.osm" 2>&1
if [ -f "$TMPDIR_TEST/out.osm" ] && grep -q "<osm" "$TMPDIR_TEST/out.osm"; then
    if ! grep -q "amenity" "$TMPDIR_TEST/out.osm"; then
        echo "  PASS: drop-tags removed amenity tag"
    else
        echo "  FAIL: amenity tag still present in output"
        exit 1
    fi
else
    echo "  FAIL: no valid output file"
    exit 1
fi

# --- Test 3: osmconvert format conversion (if available) ---
if command -v "${OSMCONVERT_BIN}" >/dev/null 2>&1; then
    echo "[test] osmconvert OSM to o5m"
    "${OSMCONVERT_BIN}" "$TMPDIR_TEST/test.osm" -o="$TMPDIR_TEST/test.o5m" 2>&1
    if [ -f "$TMPDIR_TEST/test.o5m" ] && [ -s "$TMPDIR_TEST/test.o5m" ]; then
        echo "  PASS: osmconvert OSM->o5m OK"
    else
        echo "  FAIL: osmconvert OSM->o5m failed"
        exit 1
    fi
fi

echo "[test] All tests passed"
