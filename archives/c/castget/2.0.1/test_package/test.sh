#!/bin/sh
# castget consumer test — real end-to-end behaviour via the packaged binary.
# Usage: test.sh <castget-binary> <package-folder>
# Prints HMBS_TEST_PACKAGE_RESULT=<json> on completion.
# NOTE: deliberately no `set -o pipefail` — `prog -V | grep -q` makes grep
# exit early, the writer then dies of SIGPIPE and pipefail misreports 141.
set -eu

BIN="${1:-}"
PKG="${2:-}"

if [ -z "$BIN" ] || [ -z "$PKG" ]; then
    echo "usage: test.sh <castget-binary> <package-folder>" >&2
    exit 2
fi

WORK="$(mktemp -d "${TMPDIR:-${HOME}/tmp}/castgettest.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# 1. castget -V prints the version banner.
"$BIN" -V | grep -q 'castget'

# 2. Real RSS parsing: render a local RSS 2.0 feed, point a castgetrc at it
#    via file:// and let castget list the channel (XML parse + curl fetch).
mkdir -p "$WORK/spool"
cat > "$WORK/feed.rss" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>OHOS Test Channel</title>
    <link>http://example.org/</link>
    <description>consumer test feed</description>
    <item>
      <title>episode one</title>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
      <enclosure url="file://$WORK/ep1.mp3" length="4" type="audio/mpeg"/>
    </item>
  </channel>
</rss>
EOF
cat > "$WORK/castgetrc" <<EOF
[test]
url=file://$WORK/feed.rss
spool=$WORK/spool
EOF

"$BIN" --list -C "$WORK/castgetrc" > "$WORK/list.out"
grep -q 'test' "$WORK/list.out"

# 3. Full catchup run against the local feed (parses items, marks them seen).
"$BIN" --catchup -C "$WORK/castgetrc" > "$WORK/catchup.out"

# 4. A missing configuration file must fail with a clear error.
if "$BIN" --list -C "$WORK/does-not-exist.rc" > "$WORK/err.out" 2>&1; then
    echo "castget unexpectedly succeeded with a missing rcfile" >&2
    exit 1
fi

echo 'HMBS_TEST_PACKAGE_RESULT={"tool": "castget", "version": "2.0.1", "consumer_cases": 4, "passed": 4, "failed": 0}'
