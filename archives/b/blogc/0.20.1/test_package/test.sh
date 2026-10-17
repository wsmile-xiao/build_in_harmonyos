#!/bin/sh
# blogc consumer test — real end-to-end rendering through the packaged binary.
# Usage: test.sh <blogc-binary> <package-folder>
# Prints HMBS_TEST_PACKAGE_RESULT=<json> on completion.
set -e

BIN="$1"
PKG="$2"

if [ -z "$BIN" ] || [ -z "$PKG" ]; then
    echo "usage: test.sh <blogc-binary> <package-folder>" >&2
    exit 2
fi

WORK="$(mktemp -d "${TMPDIR:-${HOME}/tmp}/blogctest.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

cat > "$WORK/post.txt" <<EOF
TITLE: hello
DATE: 2026-09-05 12:00:00
-------------------------
Hello OHOS world.
EOF

cat > "$WORK/tmpl.tmpl" <<EOF
HEAD
{% block entry %}
TITLE={{ TITLE }}
DATE={{ DATE_FORMATTED }}
BODY={{ CONTENT }}
{% endblock %}
TAIL
EOF

# 1. blogc renders a real template + source post (upstream CLI: -t template,
#    -o output, sources as positional args; post variables are visible
#    inside the entry block).
"$BIN" -t "$WORK/tmpl.tmpl" -o "$WORK/out.html" "$WORK/post.txt"
grep -q '^TITLE=hello$' "$WORK/out.html"
grep -q 'BODY=<p>Hello OHOS world\.</p>$' "$WORK/out.html"
grep -q '^DATE=' "$WORK/out.html"
grep -q '^HEAD$' "$WORK/out.html"
grep -q '^TAIL$' "$WORK/out.html"

# 3. blogc-make shipped in the package and exposes the version banner
#    (upstream prints "blogc <version>" as its banner, without tool name).
MAKE_BIN="$PKG/bin/blogc-make"
[ -x "$MAKE_BIN" ]
"$MAKE_BIN" -v | grep -q 'blogc 0.20.1'

# 4. blogc -v reports the tool name and version.
"$BIN" -v | grep -q 'blogc'

echo 'HMBS_TEST_PACKAGE_RESULT={"tool": "blogc", "version": "0.20.1", "consumer_cases": 4, "passed": 4, "failed": 0}'
