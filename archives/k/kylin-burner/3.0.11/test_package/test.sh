#!/data/service/hnp/bin/bash
# test_package/test.sh — kylin-burner 3.0.11 package smoke test.
# Runs the shipped `bin/burner` launcher (--version), checks the real ELF
# binary (bin/burner-bin) and the shared libraries shipped in lib/.
# $1 = absolute path to bin/burner inside the conan package.
set -u

LAUNCHER="${1:?usage: test.sh <path-to-bin/burner>}"
PKG_BIN="$(cd "$(dirname "$LAUNCHER")" && pwd)"
PKG_ROOT="$(dirname "$PKG_BIN")"

echo "[test] launcher exists & executable: $LAUNCHER"
[ -f "$LAUNCHER" ] || { echo "❌ $LAUNCHER not found"; exit 1; }
[ -x "$LAUNCHER" ] || { echo "❌ $LAUNCHER not executable"; exit 1; }

echo "[test] $LAUNCHER --version"
OUT="$("$LAUNCHER" --version 2>&1)"
RC=$?
echo "   output: $OUT"
[ $RC -eq 0 ] || { echo "❌ burner --version exited with code $RC"; exit 1; }
case "$OUT" in
  *3.0.11*) echo "✅ burner --version output contains 3.0.11" ;;
  *)        echo "❌ burner --version output missing 3.0.11: $OUT"; exit 1 ;;
esac

echo "[test] real ELF binary: bin/burner-bin"
REAL="$PKG_BIN/burner-bin"
[ -f "$REAL" ] || { echo "❌ $REAL not found"; exit 1; }
MAGIC="$(head -c4 "$REAL" | od -An -tx1 | tr -d ' \n')"
[ "$MAGIC" = "7f454c46" ] || { echo "❌ burner-bin is not an ELF (magic: $MAGIC)"; exit 1; }
echo "✅ burner-bin is a valid ELF"

echo "[test] shared libraries in lib/"
for lib in libburner-media3.so libburner-burn3.so libburner-utils3.so; do
  if [ -f "$PKG_ROOT/lib/$lib" ]; then
    echo "✅ $lib present"
  else
    echo "❌ $lib missing"; exit 1
  fi
done

echo "kylin-burner test_package: ALL PASS"
exit 0
