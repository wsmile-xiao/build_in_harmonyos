#!/data/service/hnp/bin/bash
# test_package/run_check.sh — runs the signed consumer test binary and
# verifies the generated PDF (upstream tests.sh asserts, pure-stdlib
# Python port — no third-party packages needed: pypdf is NOT available
# on the CI workers, so the structural asserts parse the raw PDF bytes:
# header magic, page object count, /Count, embedded text (utf8→WinAnsi
# octal + escaped control characters), bookmark tree, metadata, xref/EOF).
# Requires: $1 = binary path (absolute or relative).
set -euo pipefail

BIN="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
cd "$OUT"

# Step 1: generate output.pdf via the consumer binary (full API pass,
# prints "ok:" lines and ends with failures=0)
LOG="$OUT/run.txt"
"$BIN" > "$LOG" 2>&1
cat "$LOG"
tail -1 "$LOG" | grep -q "^failures=0$" || { echo "consumer binary reported failures"; exit 1; }

# Step 2: assert the PDF structure (upstream tests.sh port — pdftotext +
# pdftk asserts re-expressed as raw-PDF byte checks; zero deps)
python3 - << 'PYEOF'
import re
import sys

data = open("output.pdf", "rb").read()

checks = []
# pdftk "NumberOfPages: 4" — page objects (exclude /Pages tree node)
page_objs = len(re.findall(rb"/Type\s*/Page[^s]", data))
checks.append(("page count = 4 (pdftk NumberOfPages; /Type /Page objects)",
               page_objs == 4 and b"/Count 4" in data))
# pdftotext utf8 extraction — pdfgen encodes the UTF-8 supplementary
# chars into single-byte WinAnsi (the '€' as \200 octal, Ü as \xdc, ...)
checks.append(("utf8 special characters embedded (€ÜŽžŠšÁáüöäÄÜÖß)",
               b"Special characters: \\200\xdc\x8e\x9e\x8a\x9a\xc1\xe1\xfc\xf6\xe4\xc4\xdc\xd6\xdf" in data))
# pdftotext control-char extraction — PDF string escapes: \( \)
checks.append(("control characters embedded (( ) < > [ ] { } / %)",
               b"Control characters \\( \\) < > [ ] { } / %" in data))
# page text present (Page Two on page 2)
checks.append(("page text present (Page Two)", b"(Page Two)" in data))
# pdftk "BookmarkTitle: First page" — outline entry
checks.append(("bookmark 'First page' (pdftk BookmarkTitle)",
               b"/Title (First page)" in data))
# pdftk "InfoValue: My subject" — document metadata
checks.append(("subject metadata (pdftk InfoValue: My subject)",
               b"/Subject (My subject)" in data))
# PDF header magic + trailer integrity
checks.append(("PDF header magic %PDF-1.3", data[:8] == b"%PDF-1.3"))
checks.append(("xref + EOF trailer present",
               b"xref" in data[-3000:] and data.rstrip().endswith(b"%%EOF")))

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(("ok: " if ok else "FAIL: ") + name)
if failed:
    sys.exit(1)
print("PDF structure checks: %d/%d passed" % (len(checks) - len(failed), len(checks)))
PYEOF
echo "OK: pdfgen consumer test + PDF structure checks all passed"
