#!/bin/sh
# test_package/test.sh — functional smoke test for the verovio CLI.
# Runs inside the conanrun env (PATH includes the installed bin/).
# Requires VEROVIO_RESOURCE_DIR to point at the installed share/verovio data
# (SMuFL bounding-box XML, glyph dirs, text/ and the fonts CSS).
#
# Device note (round-13/14): on the HarmonyOS PC preflight sandbox files created
# by the verovio CLI itself (std::ofstream -> <out>.svg) are not visible
# afterwards even though the CLI prints "Output written to ..." and exits 0;
# files created by the shell ARE visible. The render result is therefore read
# from the CLI's stdout (-o -), which flows through the shell's pipe and is
# visible. This still renders the real MEI score through the real render
# pipeline and asserts a non-empty SVG with a <svg> root element.
#
# Emits 4 checks (all always run) and writes a machine-readable result JSON to
# $HMBS_TP_RESULT (discovered/passed), so the test_package conanfile can report
# honest counts instead of a hardcoded value. Every check increments TOTAL
# regardless of outcome, and PASS only on success.
set -u

RESULT_JSON="${HMBS_TP_RESULT:-}"
if [ -z "$RESULT_JSON" ]; then
    echo "FATAL: HMBS_TP_RESULT not set" >&2
    exit 1
fi

command -v verovio >/dev/null 2>&1 || { echo "FATAL: verovio not on PATH"; exit 1; }

RES="${VEROVIO_RESOURCE_DIR:-}"
if [ -z "$RES" ] || [ ! -d "$RES" ]; then
    echo "FATAL: VEROVIO_RESOURCE_DIR is not a directory: '$RES'"
    exit 1
fi

# Scratch space. OHOS /tmp is often read-only — use $TMPDIR/$HOME/tmp.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TDIR="$SCRATCH/verovio-test-$$"
mkdir -p "$TDIR"
trap 'rm -rf "$TDIR"' EXIT

pass=0
total=0
# record <name> <result(PASS|FAIL)>
record() {
    total=$((total + 1))
    if [ "$2" = "PASS" ]; then
        pass=$((pass + 1))
        echo "  PASS: $1"
    else
        echo "  FAIL: $1"
    fi
}

# ---- Check 1: --version banner ----
echo "[check 1/4] verovio --version"
VER="$(verovio --version 2>&1)"
if [ $? -eq 0 ]; then
    case "$VER" in
        Verovio*) record "--version printed banner: $VER" PASS ;;
        *) record "--version output unexpected: '$VER'" FAIL ;;
    esac
else
    record "verovio --version exited non-zero: '$VER'" FAIL
fi

# ---- Prepare a real MEI score ----
MEI="$TDIR/sample.mei"
cat > "$MEI" <<'MEIEOF'
<?xml version="1.0" encoding="UTF-8"?>
<mei xmlns="http://www.music-encoding.org/ns/mei" meiVersion="4.0.0">
  <meiHead><fileDesc><titleStmt><title>smoke test</title></titleStmt><pubStmt/></fileDesc></meiHead>
  <music><body>
    <mdiv><score>
      <scoreDef meter.count="4" meter.unit="4">
        <staffGrp><staffDef n="1" lines="5" clef.shape="G" clef.line="2"/></staffGrp>
      </scoreDef>
      <section>
        <measure n="1">
          <staff n="1"><layer n="1">
            <note dur="4" oct="4" pname="c"/>
            <note dur="4" oct="4" pname="d"/>
            <note dur="4" oct="4" pname="e"/>
            <note dur="4" oct="4" pname="f"/>
          </layer></staff>
        </measure>
      </section>
    </score></mdiv>
  </music></body>
</mei>
MEIEOF
if [ ! -s "$MEI" ]; then
    echo "FATAL: could not write sample MEI" >&2
    exit 1
fi

# ---- Check 2: render MEI -> SVG (captured on stdout via -o -) ----
echo "[check 2/4] verovio -r RES -o - sample.mei"
SVG="$(verovio -r "$RES" -o - "$MEI" 2>"$TDIR/render.err")"
RENDERC=$?
if [ $RENDERC -eq 0 ]; then
    record "verovio render exited 0" PASS
else
    record "verovio render exited non-zero ($RENDERC)" FAIL
    echo "  (render.stderr)"
    sed 's/^/    /' "$TDIR/render.err" | tail -30
fi
echo "  (render-err bytes: $(wc -c < "$TDIR/render.err" 2>/dev/null || echo 0) svg-bytes-on-stdout: $(printf '%s' "$SVG" | wc -c))"

# ---- Check 3: SVG output is non-empty ----
echo "[check 3/4] SVG output non-empty"
if [ -n "$SVG" ]; then
    record "SVG non-empty ($(printf '%s' "$SVG" | wc -c) bytes)" PASS
else
    record "SVG output is empty/missing" FAIL
    echo "  (render.stderr tail)"
    sed 's/^/    /' "$TDIR/render.err" | tail -40
fi

# ---- Check 4: SVG root element ----
echo "[check 4/4] SVG root element"
case "$SVG" in
    *'<svg'*) record "SVG contains <svg> root" PASS ;;
    *) record "SVG does not contain <svg> root" FAIL ;;
esac

echo "test.sh summary: discovered=$total executed=$total passed=$pass failed=$((total - pass)) skipped=0 $([ "$pass" -eq "$total" ] && echo OK || echo FAILED)"

# Machine single-source result for the test_package conanfile.
if command -v python3 >/dev/null 2>&1; then
    python3 - "$RESULT_JSON" "$total" "$pass" <<'PYEOF'
import json, sys
path = sys.argv[1]
total = int(sys.argv[2])
passed = int(sys.argv[3])
with open(path, "w", encoding="utf-8") as fh:
    json.dump({"discovered": total, "passed": passed, "failed": total - passed}, fh)
PYEOF
else
    # Fallback: same counters, written directly (still the single source).
    printf '{"discovered": %d, "passed": %d, "failed": %d}\n' "$total" "$pass" "$((total - pass))" > "$RESULT_JSON"
fi

[ "$pass" -eq "$total" ] && exit 0 || exit 1
