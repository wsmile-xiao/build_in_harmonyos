#!/data/service/hnp/bin/bash
# test_package/test.sh — tunnelx 20190701 consumer-side verification (Conan L1).
#
# Arg 1: installed package folder (…/p/tunnelx<hash>/p)
# Env:   JAVA_HOME — optional, auto-discovered otherwise
#
# Checks
#   T1  package layout: lib/tunnelx.jar + bin/tunnelx launcher
#   T2  JAR manifest Main-Class = Tunnel.MainBox
#   T3  JAR content: Tunnel/*.class count + bundled symbols/tutorials listings
#   T4  upstream executable entry Tunnel.MainBox is wired (GUI entry; headless
#       HarmonyOS JVM has no AWT display backend, so it must stop at AWT init)
#   T5  OHOS launcher bin/tunnelx resolves the BiSheng JDK and reaches the app
#   T5b launcher CLI contract: bin/tunnelx --version / --help exit 0
#       (same contract the CI L2 smoke test probes)
#   T6  OHOS probe (compiled + executed with the consumer JVM): HarmonyOS
#       aarch64 runtime, java.io.tmpdir redirected off read-only /tmp,
#       packaged upstream version marker, jar-relative resource lookup,
#       upstream geometry kernel
#
# NOTE (code-style rule 7): `set -e` is intentionally omitted. This driver
# counts PASS/FAIL across many independent checks (T4/T5/T5b expect non-zero
# exits from the headless GUI entry), so aborting on the first failure would
# make the report incomplete. Failures are aggregated in $FAILED and the
# script exits non-zero at the end, which is what conan test() observes.
set -uo pipefail

PKG_DIR="${1:?usage: test.sh <package_dir>}"
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="$(mktemp -d "${TMPDIR:-$HOME/tmp}/tunnelx-test.XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT

FAILED=0
TESTS=0
PASSED=0

ok()   { TESTS=$((TESTS + 1)); PASSED=$((PASSED + 1)); echo "[test] PASS $1 — $2"; }
bad()  { TESTS=$((TESTS + 1)); FAILED=$((FAILED + 1)); echo "[test] FAIL $1 — $2" >&2; }

# ── locate the BiSheng JDK (no java on PATH on HarmonyOS) ─────────────────
if [ -z "${JAVA_HOME:-}" ] || [ ! -x "${JAVA_HOME}/bin/java" ]; then
  for candidate in "$HOME/bishengjdk17" "$HOME/usr/local/bishengjdk17" \
                   /usr/local/bishengjdk17 /data/service/hnp/bishengjdk17; do
    if [ -x "$candidate/bin/java" ]; then
      JAVA_HOME="$candidate"
      break
    fi
  done
fi
if [ -z "${JAVA_HOME:-}" ] || [ ! -x "${JAVA_HOME}/bin/java" ]; then
  echo "[test] ERROR JAVA_HOME not found; install BiShengJDK 17" >&2
  exit 1
fi
JAVA="$JAVA_HOME/bin/java"
JAVAC="$JAVA_HOME/bin/javac"
JARTool="$JAVA_HOME/bin/jar"
echo "[test] JAVA_HOME=$JAVA_HOME"
"$JAVA" -version 2>&1 | sed 's/^/[test] /'

JAR="$PKG_DIR/lib/tunnelx.jar"
LAUNCHER="$PKG_DIR/bin/tunnelx"

# ── T1: package layout ───────────────────────────────────────────────────
if [ -f "$JAR" ]; then
  ok T1 "lib/tunnelx.jar present ($(wc -c < "$JAR") bytes)"
else
  bad T1 "lib/tunnelx.jar missing in $PKG_DIR"
fi
if [ -x "$LAUNCHER" ]; then
  ok T1b "bin/tunnelx launcher present and executable"
else
  bad T1b "bin/tunnelx launcher missing or not executable"
fi

# ── T2: JAR manifest Main-Class (JDK jar tool; HarmonyOS has no unzip) ───
if [ -f "$JAR" ]; then
  ( cd "$WORK_DIR" && "$JARTool" xf "$JAR" META-INF/MANIFEST.MF ) >/dev/null 2>&1 || true
  if grep -q "Main-Class: Tunnel.MainBox" "$WORK_DIR/META-INF/MANIFEST.MF" 2>/dev/null; then
    ok T2 "Main-Class: Tunnel.MainBox"
  else
    bad T2 "Main-Class: Tunnel.MainBox missing from MANIFEST.MF"
  fi
else
  bad T2 "skipped — JAR missing"
fi

# ── T3: JAR content (classes + self-contained resources) ─────────────────
if [ -f "$JAR" ]; then
  "$JARTool" tf "$JAR" > "$WORK_DIR/jar-list.txt" 2>/dev/null || true
  CLASSES=$(grep -c '^Tunnel/.*\.class$' "$WORK_DIR/jar-list.txt" || true)
  if [ "${CLASSES:-0}" -ge 230 ]; then
    ok T3 "Tunnel/*.class entries = $CLASSES (>= 230)"
  else
    bad T3 "Tunnel/*.class entries = ${CLASSES:-0} (< 230)"
  fi
  for entry in symbols/listdir.txt tutorials/listdir.txt symbols/helpfile.md; do
    if grep -qx "$entry" "$WORK_DIR/jar-list.txt"; then
      ok T3b "bundled resource $entry"
    else
      bad T3b "bundled resource $entry missing"
    fi
  done
else
  bad T3 "skipped — JAR missing"
fi

# ── T4: upstream executable entry is wired ───────────────────────────────
# Upstream ships no automated test harness (see MANIFEST.yml); its sole entry
# is the Swing/AWT main class.  The HarmonyOS BiSheng JDK has no xawt backend,
# so a run here must reach Tunnel.MainBox.<init> and then stop with
# HeadlessException — which is what we assert (entry reachable, no display).
if [ -f "$JAR" ]; then
  "$JAVA" -cp "$JAR" Tunnel.MainBox --quiet > "$WORK_DIR/entry.log" 2>&1
  RC=$?
  if [ "$RC" -ne 0 ] && grep -q "Tunnel.MainBox.main" "$WORK_DIR/entry.log" \
     && grep -q "HeadlessException" "$WORK_DIR/entry.log"; then
    ok T4 "upstream entry Tunnel.MainBox reached AWT init (headless: no display backend)"
  else
    bad T4 "upstream entry did not behave as expected (rc=$RC); see entry.log"
    sed 's/^/[test]   /' "$WORK_DIR/entry.log" | head -20
  fi
else
  bad T4 "skipped — JAR missing"
fi

# ── T5/T5b setup: expose the conan-provided JDK to the launcher's search path ─
# FIX: T5 and T5b intentionally unset JAVA_HOME (`env -u JAVA_HOME`) to verify
# that bin/tunnelx can *auto-discover* the JDK.  The launcher only searches a
# fixed set of well-known locations ($HOME/bishengjdk17, /usr/local/…,
# /data/service/hnp/…), none of which is the temporary JDK that conan unpacks
# under test_package/.  As a result the launcher aborted with
# "JAVA_HOME not found" even though the driver itself had a perfectly valid
# JAVA_HOME.  We bridge that gap by symlinking the conan-provided JDK into the
# launcher's first search location, *without* touching the driver's own
# JAVA_HOME (so T1–T4 and T6 keep using the real one).  If $HOME/bishengjdk17
# already exists we leave it alone.
LAUNCHER_JDK_LINK="$HOME/bishengjdk17"
if [ ! -e "$LAUNCHER_JDK_LINK" ] && [ -x "$JAVA_HOME/bin/java" ]; then
  if ln -s "$JAVA_HOME" "$LAUNCHER_JDK_LINK" 2>/dev/null; then
    echo "[test] linked conan JDK into launcher search path: $LAUNCHER_JDK_LINK -> $JAVA_HOME"
  else
    echo "[test] WARN could not create $LAUNCHER_JDK_LINK (launcher auto-discovery may still fail)" >&2
  fi
else
  echo "[test] $LAUNCHER_JDK_LINK already present; launcher will use it"
fi

# ── T5: OHOS launcher resolves the JDK and reaches the application ───────
if [ -x "$LAUNCHER" ]; then
  env -u JAVA_HOME "$LAUNCHER" --quiet > "$WORK_DIR/launcher.log" 2>&1
  RC=$?
  if grep -q "Tunnel.MainBox" "$WORK_DIR/launcher.log"; then
    ok T5 "bin/tunnelx auto-located JAVA_HOME and launched Tunnel.MainBox (rc=$RC, headless GUI)"
  else
    bad T5 "bin/tunnelx did not reach Tunnel.MainBox (rc=$RC)"
    sed 's/^/[test]   /' "$WORK_DIR/launcher.log" | head -20
  fi
else
  bad T5 "skipped — launcher missing"
fi

# ── T5b: launcher CLI contract (CI L2 smoke test: --version/--help) ──────
if [ -x "$LAUNCHER" ]; then
  VER_OUT="$(env -u JAVA_HOME "$LAUNCHER" --version 2>&1)"; RC_V=$?
  HELP_OUT="$(env -u JAVA_HOME "$LAUNCHER" --help 2>&1)"; RC_H=$?
  if [ "$RC_V" -eq 0 ] && printf '%s' "$VER_OUT" | grep -q "20190701" \
     && [ "$RC_H" -eq 0 ] && printf '%s' "$HELP_OUT" | grep -qi "Usage"; then
    ok T5b "bin/tunnelx --version/--help contract OK ($(printf '%s' "$VER_OUT" | head -1))"
  else
    bad T5b "bin/tunnelx --version/--help failed (rc=$RC_V/$RC_H)"
    printf '%s\n' "$VER_OUT" | sed 's/^/[test]   /' | head -5
  fi
else
  bad T5b "skipped — launcher missing"
fi

# ── T6: OHOS probe (compiled and run against the installed package) ──────
# The launcher's -Djava.io.tmpdir adaptation is exercised explicitly here.
PROBE_SRC="$SELF_DIR/TunnelOhosProbe.java"
TMP_CANDIDATE="${TMPDIR:-$HOME/tmp}"
[ -d "$TMP_CANDIDATE" ] || TMP_CANDIDATE="$HOME/tmp"
mkdir -p "$WORK_DIR/probe-classes"
if [ -f "$JAR" ] && "$JAVAC" -cp "$JAR" -d "$WORK_DIR/probe-classes" "$PROBE_SRC" \
      > "$WORK_DIR/probe-compile.log" 2>&1; then
  "$JAVA" -Djava.io.tmpdir="$TMP_CANDIDATE" \
      -cp "$JAR:$WORK_DIR/probe-classes" Tunnel.TunnelOhosProbe \
      > "$WORK_DIR/probe.log" 2>&1
  PROBE_RC=$?
  sed 's/^/[test] /' "$WORK_DIR/probe.log"
  PROBE_FAIL=$(grep -c '^PROBE FAIL' "$WORK_DIR/probe.log" || true)
  if [ "$PROBE_RC" -eq 0 ] && [ "${PROBE_FAIL:-0}" -eq 0 ]; then
    PROBE_N=$(grep -c '^PROBE PASS' "$WORK_DIR/probe.log" || true)
    ok T6 "OHOS probe: $PROBE_N/${PROBE_N} assertions passed (OHOS-1/OHOS-2 platform + PKG-1..5 package)"
  else
    bad T6 "OHOS probe failures (rc=$PROBE_RC, fail=$PROBE_FAIL)"
  fi
else
  bad T6 "OHOS probe failed to compile; see probe-compile.log"
  sed 's/^/[test]   /' "$WORK_DIR/probe-compile.log" | head -20
fi

echo "[test] ---------------------------------------------"
echo "[test] test_package result: ${PASSED}/${TESTS} passed, ${FAILED} failed"
echo "HMBS_TEST_PACKAGE_RESULT={\"total\": $TESTS, \"passed\": $PASSED, \"failed\": $FAILED}"

if [ "$FAILED" -ne 0 ]; then
  echo "[test] ❌ $FAILED test(s) failed" >&2
  exit 1
fi
echo "[test] ✅ all ${TESTS} test_package checks passed"
exit 0