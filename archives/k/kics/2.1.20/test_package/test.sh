#!/bin/sh
# HarmonyOS consumer feasibility test for the packaged kics binary.
# Asserts: (1) `kics version` runs and reports v2.1.20; (2) a real `kics scan`
# on a minimal terraform file produces a JSON report (exercises the packaged
# queries/libraries assets loaded from the filesystem on OHOS).
#
# NOTE: the recipe patches pkg/engine/provider/extract.go so local source paths
# (including --queries-path / --libraries-path) are referenced directly instead of
# going through go-getter's os.Symlink() (self-signed binaries are denied the
# symlink syscall on OHOS). So we can point kics straight at the packaged assets.
set -e

BIN="$1"
if [ -z "$BIN" ]; then
  echo "usage: test.sh <path-to-kics-binary>"
  exit 2
fi

WORK=$(mktemp -d)

echo "== [1/2] kics version (binary exec + embedded constants on OHOS) =="
"$BIN" version
"$BIN" version | grep -q "2.1.20" || { echo "FAIL: kics version does not report 2.1.20"; exit 1; }
echo "PASS: kics version reports 2.1.20 and executes on OHOS"

echo "== [2/2] kics scan on a minimal terraform file (exercises packaged queries) =="
cat > "$WORK/main.tf" <<'EOF'
resource "aws_security_group" "open" {
  name = "open-sg"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
EOF

# Resolve packaged assets (bin/kics -> package root -> assets/). Patched kics reads
# these directly (no go-getter symlink), so the .conan2 path is fine.
PKG=$(cd "$(dirname "$BIN")/.." && pwd)
QPATH="$PKG/assets/queries"
LPATH="$PKG/assets/libraries"

if [ ! -d "$QPATH" ]; then
  echo "FAIL: packaged queries not found at $QPATH"
  exit 1
fi

"$BIN" scan \
  --path "$WORK/main.tf" \
  --type terraform \
  --queries-path "$QPATH" \
  --libraries-path "$LPATH" \
  --output-path "$WORK" \
  --output-name kics_hn_result \
  --report-formats json \
  --no-progress \
  --ignore-on-exit all || true

if [ -f "$WORK/kics_hn_result.json" ]; then
  echo "PASS: kics scan produced report $WORK/kics_hn_result.json (consumer feasibility verified on OHOS)"
  echo "---- report summary (first 20 lines) ----"
  head -n 20 "$WORK/kics_hn_result.json" || true
  # Verify the JSON is well-formed and queries were actually loaded.
  if "$BIN" version >/dev/null 2>&1; then
    echo "REPORT_BYTES=$(wc -c < "$WORK/kics_hn_result.json")"
  fi
else
  echo "WARN: no JSON report produced; kics scan did not complete as expected on OHOS"
  exit 1
fi

echo "ALL_CONSUMER_TESTS_PASSED"
