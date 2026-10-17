#!/data/service/hnp/bin/bash
# test_package/test.sh - functional test for the di-edid-decode executable.
# Runs inside the conanrun env (PATH already contains the packaged bin/).
set -euo pipefail

SELF="${BASH_SOURCE[0]:-$0}"
DIR="$(cd "$(dirname "$SELF")" && pwd)"
cd "$DIR"

command -v di-edid-decode >/dev/null || {
    echo "di-edid-decode is not on PATH"
    exit 1
}

# 1) --version must succeed.  Upstream only knows -h and returns -1 from both
#    the -h and the unknown-option paths, so this asserts patch 0001.
echo "[test] di-edid-decode --version"
VERSION_OUT="$(di-edid-decode --version)"
case "$VERSION_OUT" in
    *0.3.0*) echo "        [ok] $VERSION_OUT" ;;
    *) echo "di-edid-decode --version did not report 0.3.0: $VERSION_OUT"; exit 1 ;;
esac

# 2) --help must exit 0 as well (upstream used to return -1 here).
echo "[test] di-edid-decode --help"
di-edid-decode --help >/dev/null 2>&1
echo "        [ok] --help exit status 0"

# /tmp is read-only on OHOS - use a scratch dir under $HOME instead.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/libdisplay-info-tools-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

# Materialize the upstream EDID fixture (test/data/acer-p1276.edid).  It is
# stored as base64 text because a PR diff cannot carry binary blobs through
# the shared CI checkout (R02).
python3 - "$DIR/data/acer-p1276.edid.b64" "$TESTDIR/acer-p1276.edid" <<'PYEOF'
import base64
import hashlib
import pathlib
import sys

EXPECTED = "4206fd5055f87232ff2b621040cb77d4e490e0d7d2b4f2c6d048ea6310fd386a"
data = base64.b64decode(
    "".join(pathlib.Path(sys.argv[1]).read_text(encoding="ascii").split())
)
digest = hashlib.sha256(data).hexdigest()
assert digest == EXPECTED, f"fixture sha256 mismatch: {digest} != {EXPECTED}"
assert len(data) == 256, "fixture is not a 1 base block + 1 extension EDID"
pathlib.Path(sys.argv[2]).write_bytes(data)
PYEOF

SIZE=$(wc -c < "$TESTDIR/acer-p1276.edid")
[ "$SIZE" -eq 256 ] || { echo "EDID fixture was not written"; exit 1; }
echo "[test] fixture ready: acer-p1276.edid ($SIZE bytes)"

# 3) decode a real panel EDID: exit status 0 and a conforming report.
echo "[test] di-edid-decode acer-p1276.edid"
OUT="$TESTDIR/acer-p1276.out"
di-edid-decode "$TESTDIR/acer-p1276.edid" > "$OUT"
grep -q "EDID conformity: PASS" "$OUT" || {
    echo "no conformity verdict in the decoded report"
    cat "$OUT"
    exit 1
}
grep -q "Block 1, CTA-861 Extension Block" "$OUT" || {
    echo "the CTA-861 extension block was not decoded"
    cat "$OUT"
    exit 1
}
echo "        [ok] decoded $(wc -l < "$OUT") lines, conformity PASS"

# 4) negative control: an empty EDID blob must not be reported as a success.
echo "[test] di-edid-decode <empty input> (expected failure)"
if di-edid-decode < /dev/null >/dev/null 2>&1; then
    echo "di-edid-decode reported success for an empty EDID blob"
    exit 1
fi
echo "        [ok] empty input rejected"

echo "All tests passed."