#!/bin/bash
# test_package smoke + functional test for kingfisher 1.109.0
#
# R34: this script really executes the packaged `kingfisher` binary and asserts
# on its observed behaviour — it never just prints "ok".
#   1. `--version` must report the packaged version.
#   2. a scan over a fixture with known synthetic credentials must actually
#      DETECT them (findings >= 1) — a stub binary or a broken regex engine
#      cannot pass this.
#   3. a clean file must produce zero findings (guards against a fake scanner
#      that reports everything).
set -e

if [ -z "$KINGFISHER_BIN" ]; then
    echo "ERROR: KINGFISHER_BIN not set" >&2
    exit 1
fi
if [ ! -x "$KINGFISHER_BIN" ]; then
    echo "ERROR: kingfisher binary not executable: $KINGFISHER_BIN" >&2
    exit 1
fi

WORK=$(mktemp -d 2>/dev/null || mktemp -d "$HOME/tmp/kftest.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

# ── Test 1: version reporting ──────────────────────────────────────────────
echo "== Test 1: kingfisher --version =="
VERSION_OUT=$("$KINGFISHER_BIN" --version 2>&1)
echo "$VERSION_OUT"
if ! echo "$VERSION_OUT" | grep -q "1.109.0"; then
    echo "FAIL: --version does not report 1.109.0" >&2
    exit 1
fi

# ── Test 2: real detection over a synthetic credential fixture ─────────────
echo "== Test 2: detect synthetic credentials =="
cat > "$WORK/leaked.py" <<'EOF'
# synthetic credentials for test purposes only (not real secrets)
AWS_ACCESS_KEY_ID = "AKIA6ODU5DHT7VPXGCE4"
AWS_SECRET_ACCESS_KEY = "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"
EOF

"$KINGFISHER_BIN" scan -f json "$WORK/leaked.py" > "$WORK/leaked.json" 2>/dev/null || true
FINDINGS=$(tr -d '\n' < "$WORK/leaked.json" | sed -n 's/.*"findings":\([0-9]*\).*/\1/p' | tail -1)
echo "leaked.py findings=$FINDINGS"
if [ -z "$FINDINGS" ] || [ "$FINDINGS" -lt 1 ]; then
    echo "FAIL: scanner did not detect the synthetic AWS credentials (findings=$FINDINGS)" >&2
    exit 1
fi
tr -d '\n' < "$WORK/leaked.json" | grep -q '"AWS Secret Access Key"' || {
    echo "FAIL: expected rule 'AWS Secret Access Key' in findings_by_rule" >&2
    exit 1
}

# ── Test 3: clean input yields zero findings ───────────────────────────────
echo "== Test 3: clean input reports no findings =="
printf 'def add(a, b):\n    return a + b\n' > "$WORK/clean.py"
"$KINGFISHER_BIN" scan -f json "$WORK/clean.py" > "$WORK/clean.json" 2>/dev/null || true
CLEAN=$(tr -d '\n' < "$WORK/clean.json" | sed -n 's/.*"findings":\([0-9]*\).*/\1/p' | tail -1)
echo "clean.py findings=$CLEAN"
if [ "$CLEAN" != "0" ]; then
    echo "FAIL: clean file produced findings ($CLEAN); scanner over-reports" >&2
    exit 1
fi

# ── Test 4: the Vectorscan rule engine is actually loaded ──────────────────
echo "== Test 4: rule engine loaded =="
RULES=$(tr -d '\n' < "$WORK/leaked.json" | sed -n 's/.*"rules_applied":\([0-9]*\).*/\1/p' | tail -1)
echo "rules_applied=$RULES"
if [ -z "$RULES" ] || [ "$RULES" -lt 100 ]; then
    echo "FAIL: expected the built-in ruleset to be loaded (rules_applied=$RULES)" >&2
    exit 1
fi

echo "kingfisher test_package: PASS (4/4)"
