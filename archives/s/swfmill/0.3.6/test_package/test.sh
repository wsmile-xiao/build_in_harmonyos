#!/bin/sh
# test_package consumer test for swfmill 0.3.6 (CLI application).
#
# Usage: test.sh <swfmill-binary> <share-dir> <workdir> <target-os>
#
# 1) xml2swf  — minimal XML -> SWF        (asserted: output exists + non-empty)
# 2) swf2xml  — SWF -> XML round-trip     (asserted: output exists + non-empty)
# 3) xslt     — OHOS-only observation      (rule12: NON-assertive, prints only)
#
# The XML dialect used below is the swfml low-level one (same as upstream
# test/xml-swf-round-trip); the simple <movie> dialect would require an
# swfmill namespace declaration.
export PATH="$PATH:/system/bin"

SWFMILL="$1"
SHARE_DIR="$2"
WORKDIR="$3"
TARGET_OS="${4:-}"

echo "--- swfmill consumer verification ---"
[ -n "$SWFMILL" ] || { echo "FAIL: missing swfmill binary argument"; exit 1; }
[ -x "$SWFMILL" ] || { echo "FAIL: swfmill binary not executable at $SWFMILL"; exit 1; }

# --- Test 1: xml2swf (smoke — generate SWF from minimal XML) ---
cat > "$WORKDIR/minimal.xml" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<swf version="4" compressed="0">
  <Header framerate="12" frames="1">
    <size>
      <Rectangle left="0" right="11000" top="0" bottom="8000"/>
    </size>
    <tags>
      <SetBackgroundColor>
        <Color red="255" green="255" blue="255"/>
      </SetBackgroundColor>
      <ShowFrame/>
      <End/>
    </tags>
  </Header>
</swf>
XML
"$SWFMILL" xml2swf "$WORKDIR/minimal.xml" "$WORKDIR/minimal.swf"
rc=$?
[ "$rc" = "0" ] || { echo "FAIL: xml2swf exit=$rc"; exit 1; }
[ -s "$WORKDIR/minimal.swf" ] || { echo "FAIL: xml2swf produced no output"; exit 1; }
echo "PASS 1: xml2swf -> $(wc -c < "$WORKDIR/minimal.swf") bytes"

# --- Test 2: swf2xml (round-trip — convert back to XML) ---
"$SWFMILL" swf2xml "$WORKDIR/minimal.swf" "$WORKDIR/minimal.swf.xml"
rc=$?
[ "$rc" = "0" ] || { echo "FAIL: swf2xml exit=$rc"; exit 1; }
[ -s "$WORKDIR/minimal.swf.xml" ] || { echo "FAIL: swf2xml produced no output"; exit 1; }
echo "PASS 2: swf2xml -> $(wc -c < "$WORKDIR/minimal.swf.xml") bytes"

# --- Test 3: HarmonyOS-specific consumer feasibility (rule12) ---
# Verify the binary runs natively on OHOS and drives the XSLT engine
# (libxslt/libexslt linkage) to render a small movie. NON-ASSERTIVE by
# rule12: observations are printed only, never decide the test outcome.
if [ "$TARGET_OS" = "OHOS" ]; then
    cat > "$WORKDIR/empty.xsl" <<'XSL'
<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <swf version="4" compressed="0">
      <Header framerate="12" frames="1">
        <size>
          <Rectangle left="0" right="11000" top="0" bottom="8000"/>
        </size>
        <tags>
          <SetBackgroundColor>
            <Color red="0" green="0" blue="0"/>
          </SetBackgroundColor>
          <ShowFrame/>
          <End/>
        </tags>
      </Header>
    </swf>
  </xsl:template>
</xsl:stylesheet>
XSL
    export SWFMILL_PATH="$SHARE_DIR"
    echo "== HarmonyOS-specific consumer feasibility test (rule12, non-assertive) =="
    # Usage: swfmill xslt <stylesheet.xsl> <input.xml> [<output.swf>]
    # (upstream src/swfmill.cpp: xslfile=argv[0], infile=argv[1], outfile=argv[2])
    obs_rc=0
    "$SWFMILL" xslt "$WORKDIR/empty.xsl" "$WORKDIR/minimal.xml" "$WORKDIR/xslt-out.swf" || obs_rc=$?
    if [ -f "$WORKDIR/xslt-out.swf" ]; then
        obs_exists=yes
        obs_size=$(wc -c < "$WORKDIR/xslt-out.swf")
    else
        obs_exists=no
        obs_size=0
    fi
    echo "[obs] swfmill xslt on OHOS: rc=$obs_rc output_exists=$obs_exists output_bytes=$obs_size"
    echo "[obs] HarmonyOS consumer feasibility observation complete (non-assertive; result printed above)"
fi

echo "test swfmill 0.3.6: 2/2 asserted checks PASS"
exit 0
