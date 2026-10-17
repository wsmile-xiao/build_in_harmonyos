#!/bin/sh
set -eu
# Enable pipefail where supported (bash); ignore on generic /bin/sh (dash)
set -o pipefail 2>/dev/null || true

PKG="${1:-}"
if [ -z "$PKG" ]; then
  echo "Usage: $0 <package_folder>"
  exit 1
fi

echo "[step] bootstrap smoke test"
echo "       PKG=$PKG"

BIN="$PKG/bin/bootstrap"
JSON="$PKG/package.json"

# HMBS readonly /tmp handling: HarmonyOS mounts /tmp read-only. Use HMBS injected
# TMPDIR/TMP/TEMP (e.g. /storage/.../runtime/bootstrap-0.0.1/tmp) for any temp
# files. Previous preflight hit "can't create temporary file /tmp/sh...: Read-only
# file system". Propagate writable TMPDIR to all subprocesses.
if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ] && [ -w "$TMPDIR" ]; then
  export TMP="${TMP:-$TMPDIR}"
  export TEMP="${TEMP:-$TMPDIR}"
elif [ -n "${TMP:-}" ] && [ -d "$TMP" ] && [ -w "$TMP" ]; then
  export TMPDIR="$TMP"
  export TEMP="${TEMP:-$TMP}"
elif [ -n "${TEMP:-}" ] && [ -d "$TEMP" ] && [ -w "$TEMP" ]; then
  export TMPDIR="$TEMP"
  export TMP="${TMP:-$TEMP}"
else
  # Fallback to writable location inside package folder
  TMPDIR="$PKG/tmp"
  mkdir -p "$TMPDIR" 2>/dev/null || true
  export TMPDIR TMP="$TMPDIR" TEMP="$TMPDIR"
fi
# Ensure node / mktemp respect the writable dir
export TMPDIR TMP TEMP

# 1. File existence (HMDFS chmod=0 makes -x unreliable; use -f primary)
if [ ! -f "$BIN" ]; then
  echo "        [fail] $BIN not found"
  exit 1
fi
echo "        [ok] bin/bootstrap exists"
if [ -x "$BIN" ]; then
  echo "        [ok] bin/bootstrap executable"
else
  echo "        [warn] $BIN not executable (HMDFS chmod=0, expected), continuing with node invocation"
fi

# 2. package.json exists and version correct
if ! grep -q '"version": "0.0.1"' "$JSON"; then
  echo "        [fail] package.json version mismatch"
  exit 1
fi
echo "        [ok] package.json version 0.0.1"

# 3. Content checks — ensure Express generator logic preserved
# Upstream splits "program" and ".version('0.0.1')" across two lines, so
# contiguous "program.version" never matches. Check tokens separately.
for pat in "program" "jadeLayout" "ejsLayout" "express_app_js" "createApplication" "commander"; do
  if ! grep -q "$pat" "$BIN"; then
    echo "        [fail] pattern $pat not found in bin/bootstrap"
    exit 1
  fi
done
# Additional version tokens that were previously checked as contiguous "program.version"
for pat in "version" "0.0.1"; do
  if ! grep -q "$pat" "$BIN"; then
    echo "        [fail] pattern $pat not found in bin/bootstrap"
    exit 1
  fi
done
echo "        [ok] template and logic patterns present"

# 4. Shebang check
if ! head -1 "$BIN" | grep -q "node"; then
  echo "        [fail] shebang missing node"
  exit 1
fi
echo "        [ok] shebang contains node"

# 5. Node runtime check — invoke via `node $BIN` to avoid needing exec bit
# When node is present the check is mandatory (fail-fast): a broken binary
# must not be masked by `|| true` or warn-only branches (R9 anti-fake-pass).
if command -v node >/dev/null 2>&1; then
  echo "[step] Node runtime check"
  if ! node "$BIN" --version 2>&1 | head -5; then
    echo "        [fail] node $BIN --version failed (binary broken)"
    exit 1
  fi
  if ! node "$BIN" --help 2>&1 | head -20; then
    echo "        [fail] node $BIN --help failed (binary broken)"
    exit 1
  fi
  if ! node "$BIN" --help 2>&1 | grep -q "sessions"; then
    echo "        [fail] --help missing sessions option (binary broken)"
    exit 1
  fi
  echo "        [ok] --help contains sessions option"
else
  echo "[step] Node not found — skipping runtime, static checks passed"
fi

echo "[ok] bootstrap 0.0.1 smoke test passed"
