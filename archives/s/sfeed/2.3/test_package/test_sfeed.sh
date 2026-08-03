#!/bin/sh
set -eu
if (set -o pipefail) 2>/dev/null; then
    set -o pipefail
fi

bin_dir=${1:?package bin directory is required}

require_tool() {
    tool=$1
    if [ ! -x "$bin_dir/$tool" ]; then
        printf 'missing executable: %s\n' "$bin_dir/$tool" >&2
        exit 1
    fi
}

check_contains() {
    file=$1
    needle=$2
    message=$3
    if ! grep -Fq "$needle" "$file"; then
        printf 'assertion failed: %s\n' "$message" >&2
        printf 'expected substring: %s\n' "$needle" >&2
        printf 'actual output:\n' >&2
        cat "$file" >&2
        exit 1
    fi
}

check_lines() {
    file=$1
    expected=$2
    actual=$(wc -l < "$file" | tr -d ' ')
    if [ "$actual" != "$expected" ]; then
        printf 'assertion failed: expected %s lines, got %s\n' "$expected" "$actual" >&2
        cat "$file" >&2
        exit 1
    fi
}

for tool in sfeed sfeed_plain sfeed_html sfeed_json sfeed_mbox sfeed_twtxt \
    sfeed_opml_import sfeed_opml_export sfeed_xmlenc; do
    require_tool "$tool"
done

workdir=$(mktemp -d "${TMPDIR:-.}/sfeed-test.XXXXXX")
trap 'rm -rf "$workdir"' EXIT HUP INT TERM

atom="$workdir/feed.xml"
tsv="$workdir/feed.tsv"
plain="$workdir/feed.txt"
html="$workdir/feed.html"
json="$workdir/feed.json"
mbox="$workdir/feed.mbox"
twtxt="$workdir/feed.twtxt"
opml="$workdir/feed.opml"
rc="$workdir/sfeedrc"
xmlenc="$workdir/xmlenc.txt"

cat > "$atom" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Feed</title>
  <link href="https://example.test/"/>
  <updated>2026-01-01T00:00:00Z</updated>
  <author><name>Tester</name></author>
  <id>urn:example:feed</id>
  <entry>
    <title>Hello Item</title>
    <link href="https://example.test/hello"/>
    <id>urn:example:hello</id>
    <updated>2026-01-01T00:00:00Z</updated>
    <author><name>Alice</name></author>
    <summary type="text">Hello summary</summary>
    <category term="news"/>
  </entry>
  <entry>
    <title>Second Item</title>
    <link href="https://example.test/second"/>
    <id>urn:example:second</id>
    <updated>2026-01-02T00:00:00Z</updated>
    <author><name>Bob</name></author>
    <content type="text">Second body</content>
    <category term="release"/>
  </entry>
</feed>
EOF

"$bin_dir/sfeed" < "$atom" > "$tsv"
check_lines "$tsv" 2
check_contains "$tsv" "Hello Item" "sfeed parsed first title"
check_contains "$tsv" "https://example.test/second" "sfeed parsed second link"
check_contains "$tsv" "Alice" "sfeed parsed author"

"$bin_dir/sfeed_plain" "$tsv" > "$plain"
check_contains "$plain" "Hello Item" "sfeed_plain contains title"

"$bin_dir/sfeed_html" "$tsv" > "$html"
check_contains "$html" "https://example.test/hello" "sfeed_html contains item link"

"$bin_dir/sfeed_json" "$tsv" > "$json"
check_contains "$json" "\"title\"" "sfeed_json emits JSON title key"
check_contains "$json" "Second Item" "sfeed_json contains second title"

"$bin_dir/sfeed_mbox" "$tsv" > "$mbox"
check_contains "$mbox" "Subject: Hello Item" "sfeed_mbox emits subject"

"$bin_dir/sfeed_twtxt" "$tsv" > "$twtxt"
check_contains "$twtxt" "Second Item" "sfeed_twtxt contains title"

cat > "$opml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
  <body>
    <outline text="Example" title="Example" type="rss" xmlUrl="https://example.test/feed.xml"/>
  </body>
</opml>
EOF

"$bin_dir/sfeed_opml_import" < "$opml" > "$rc"
check_contains "$rc" "https://example.test/feed.xml" "sfeed_opml_import imports xmlUrl"

"$bin_dir/sfeed_opml_export" "$rc" > "$opml.export"
check_contains "$opml.export" "https://example.test/feed.xml" "sfeed_opml_export exports url"

printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?>' '<feed></feed>' | "$bin_dir/sfeed_xmlenc" > "$xmlenc"
check_contains "$xmlenc" "utf-8" "sfeed_xmlenc detects XML encoding"
