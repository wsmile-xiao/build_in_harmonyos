#!/data/service/hnp/bin/bash
# test_package/test.sh — aladin 12.06 Java smoke test
# Runs the upstream test classes packaged inside Aladin.jar.
set -euo pipefail

PKG_DIR="$1"
echo "[test] aladin package dir: $PKG_DIR"

# ── Locate JAVA_HOME (bishengjdk 17+) ──
if [ -z "${JAVA_HOME:-}" ] || [ ! -f "$JAVA_HOME/bin/java" ]; then
  for candidate in "$HOME/bishengjdk17" "$HOME/usr/local/bishengjdk17" /usr/local/bishengjdk17 /data/service/hnp/bishengjdk17; do
    if [ -f "$candidate/bin/java" ]; then
      JAVA_HOME="$candidate"
      break
    fi
  done
fi
if [ -z "${JAVA_HOME:-}" ] || [ ! -f "$JAVA_HOME/bin/java" ]; then
  echo "[test] ❌ JAVA_HOME not found. Set JAVA_HOME or install bishengjdk 17." >&2
  exit 1
fi
echo "[test] using JAVA_HOME=$JAVA_HOME"
JAVA="$JAVA_HOME/bin/java"

ALADIN_JAR="$PKG_DIR/lib/Aladin.jar"
if [ ! -f "$ALADIN_JAR" ]; then
  echo "[test] ❌ Aladin.jar not found in package: $ALADIN_JAR" >&2
  exit 1
fi
echo "[test] ✅ Aladin.jar present ($(wc -c < "$ALADIN_JAR") bytes)"

# ── Manifest / main class check (use JDK jar tool, no unzip dependency) ──
# `|| true` is intentional: jar xf may fail if the entry is absent; the
# grep below then detects the missing manifest and exits 1.
TMP_BASE="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMP_BASE"
MANIFEST_TMP=$(mktemp -d "$TMP_BASE/aladin-manifest.XXXXXX")
trap 'rm -rf "$MANIFEST_TMP"' EXIT
(
  cd "$MANIFEST_TMP" && "$JAVA_HOME/bin/jar" xf "$ALADIN_JAR" META-INF/MANIFEST.MF
) >/dev/null 2>&1 || true
if grep -q "Main-Class: cds.aladin.Aladin" "$MANIFEST_TMP/META-INF/MANIFEST.MF" 2>/dev/null; then
  echo "[test] ✅ Main-Class: cds.aladin.Aladin"
  rm -rf "$MANIFEST_TMP"
else
  echo "[test] ❌ Main-Class missing/incorrect in Aladin.jar manifest" >&2
  rm -rf "$MANIFEST_TMP"
  exit 1
fi

# ── Run upstream test class: cds.astro.Test (coordinate/frame/PM assertions) ──
echo "[test] running upstream test: cds.astro.Test"
TEST_OUT=$("$JAVA" -cp "$ALADIN_JAR" cds.astro.Test 2>&1) && RC=0 || RC=$?
echo "$TEST_OUT" | tail -20
if [ $RC -ne 0 ]; then
  echo "[test] ❌ cds.astro.Test failed (exit $RC)" >&2
  exit 1
fi
echo "[test] ✅ cds.astro.Test passed"

# ── Run upstream test class: cds.astro.TestRegion (region centroid assertion) ──
echo "[test] running upstream test: cds.astro.TestRegion"
REGION_OUT=$("$JAVA" -cp "$ALADIN_JAR" cds.astro.TestRegion 2>&1) && RC=0 || RC=$?
echo "$REGION_OUT" | tail -5
if [ $RC -ne 0 ]; then
  echo "[test] ❌ cds.astro.TestRegion failed (exit $RC)" >&2
  exit 1
fi
if ! echo "$REGION_OUT" | grep -q "region centroid 123.0+34.0"; then
  echo "[test] ❌ cds.astro.TestRegion unexpected output: $REGION_OUT" >&2
  exit 1
fi
echo "[test] ✅ cds.astro.TestRegion passed"

# ── Launcher script check ──
if [ -x "$PKG_DIR/bin/aladin" ]; then
  echo "[test] ✅ bin/aladin launcher present"
else
  echo "[test] ❌ bin/aladin launcher missing or not executable" >&2
  exit 1
fi

echo "HMBS_TEST_PACKAGE_RESULT=PASS"
echo "[test] ✅ all aladin tests passed"
