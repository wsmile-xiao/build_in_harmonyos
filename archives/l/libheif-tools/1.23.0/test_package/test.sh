#!/data/service/hnp/bin/bash
# test_package/test.sh - functional test for the libheif CLI tools.
# Runs inside the conanrun env (PATH already contains the packaged bin/).
set -euo pipefail

SELF="${BASH_SOURCE[0]:-$0}"
DIR="$(cd "$(dirname "$SELF")" && pwd)"
cd "$DIR"

# 1) every installed tool must honour --version and exit 0
for tool in heif-info heif-dec heif-convert heif-enc; do
    command -v "$tool" >/dev/null || {
        echo "$tool is not on PATH"
        exit 1
    }
    echo "[test] $tool --version"
    OUT="$("$tool" --version 2>&1)"
    case "$OUT" in
        *1.23.0*) ;;
        *) echo "$tool --version did not report 1.23.0: $OUT"; exit 1 ;;
    esac
done
echo "        [ok] all four tools report version 1.23.0"

# heif-convert is the historical name of heif-dec: upstream installs it as a
# symlink, make sure the tools package preserved that.
if [ ! -L "$(command -v heif-convert)" ]; then
    echo "heif-convert is not a symlink to heif-dec"
    exit 1
fi
echo "        [ok] heif-convert is a symlink"

# /tmp is read-only on OHOS - use a scratch dir under $HOME instead.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/libheif-tools-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

# Materialize the upstream AVIF fixture (examples/example.avif).  It is stored
# as base64 text because a PR diff cannot carry binary blobs through the
# shared CI checkout (R02).
python3 - "$DIR/data/example.avif.b64" "$TESTDIR/example.avif" <<'PYEOF'
import base64
import hashlib
import pathlib
import sys

EXPECTED = "54a0dc31d02b6f5d9d4b66027d4787861b7af15ffd8fab8eab963d10c5411469"
data = base64.b64decode(
    "".join(pathlib.Path(sys.argv[1]).read_text(encoding="ascii").split())
)
digest = hashlib.sha256(data).hexdigest()
assert digest == EXPECTED, f"fixture sha256 mismatch: {digest} != {EXPECTED}"
assert data[4:8] == b"ftyp", "fixture is not an ISO-BMFF container"
pathlib.Path(sys.argv[2]).write_bytes(data)
PYEOF

SIZE=$(wc -c < "$TESTDIR/example.avif")
[ "$SIZE" -gt 0 ] || { echo "AVIF fixture was not written"; exit 1; }
echo "[test] fixture ready: example.avif ($SIZE bytes)"

# 2) heif-info on a real container
echo "[test] heif-info example.avif"
OUT="$TESTDIR/example.avif.info"
heif-info "$TESTDIR/example.avif" > "$OUT"
# heif-info 1.23.0 prints the container header, then one "image: WxH (id=N), ..."
# block per image; the fixture is a single 800x533 AVIF cover image.
grep -q "^MIME type: image/avif" "$OUT" || { echo "unexpected MIME type"; cat "$OUT"; exit 1; }
grep -q "^main brand: avif" "$OUT" || { echo "unexpected main brand"; cat "$OUT"; exit 1; }
grep -qE "^image: [0-9]+x[0-9]+ \(id=[0-9]+\), primary" "$OUT" || { echo "no primary image reported"; cat "$OUT"; exit 1; }
grep -q "^  colorspace: YCbCr, 4:2:0" "$OUT" || { echo "unexpected colorspace"; cat "$OUT"; exit 1; }
grep -q "^  bit depth: 8" "$OUT" || { echo "unexpected bit depth"; cat "$OUT"; exit 1; }
echo "        [ok] container parsed ($(wc -l < "$OUT") lines)"

# 3) negative control: a missing input must not be reported as success
echo "[test] heif-info missing.avif (expected failure)"
if heif-info "$TESTDIR/missing.avif" >/dev/null 2>&1; then
    echo "heif-info reported success for a missing file"
    exit 1
fi
echo "        [ok] missing input rejected"

echo "All tests passed."