#!/bin/sh
# Functional test for the yamdi CLI (metadata injection roundtrip).
# $1 = package bin dir.  FLV fixture is stored base64-encoded (PR 禁止
# 新增二进制文件) and decoded at test time.  Metadata content is asserted
# via yamdi's own XML export (-x, plain text) instead of grepping the
# binary FLV directly.
set -e

BINDIR="$1"
YAMDI="${BINDIR:+$BINDIR/}yamdi"

work="${TMPDIR:-.}/yamdi_test.$$"
mkdir -p "$work"
cd "$work"
trap 'cd /; rm -rf "$work"' EXIT

# 1. version/help probe exits 0 and reports the version
"$YAMDI" --version > version.out 2>&1
grep -q "Version: 1.9" version.out || { echo "FAIL: --version probe"; exit 1; }

# 2. minimal valid FLV (13 bytes: signature+header+PreviousTagSize0)
echo "RkxWAQUAAAAJAAAAAA==" | base64 -d > in.flv
[ -s in.flv ] || { echo "FAIL: fixture decode"; exit 1; }

# 3. metadata injection produces a bigger output containing onMetaData
"$YAMDI" -i in.flv -o out.flv -x out.xml
[ -s out.flv ] || { echo "FAIL: injection produced no output"; exit 1; }
[ $(wc -c < out.flv) -gt $(wc -c < in.flv) ] || { echo "FAIL: output not grown"; exit 1; }
grep -a -q "onMetaData" out.flv || { echo "FAIL: onMetaData missing"; exit 1; }

# 4. XML export confirms injected metadata (plain-text assertions)
grep -q "<hasMetadata>true</hasMetadata>" out.xml || { echo "FAIL: hasMetadata"; exit 1; }
grep -q "<flv name=" out.xml || { echo "FAIL: xml file entry"; exit 1; }

# 5. negative contract: no -i must fail with a non-zero exit
if "$YAMDI" > /dev/null 2>&1; then
    echo "FAIL: yamdi without -i exited 0"
    exit 1
fi

echo "yamdi CLI test: PASS"
