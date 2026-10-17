#!/usr/bin/env sh
# test_xelb.sh — consumer validation for the installed xelb package.
set -eu
if (set -o pipefail) 2>/dev/null; then
    set -o pipefail
fi

if [ -z "${XELB_LISPDIR:-}" ]; then
    echo "XELB_LISPDIR is not set" >&2
    exit 1
fi

for file in xcb.el xcb.elc xelb.el xelb.elc xcb-types.el xcb-xproto.el; do
    if [ ! -f "$XELB_LISPDIR/$file" ]; then
        echo "$file is missing from XELB_LISPDIR: $XELB_LISPDIR" >&2
        exit 1
    fi
done

case ":${EMACSLOADPATH:-}:" in
    *":$XELB_LISPDIR:"*) ;;
    *)
        echo "EMACSLOADPATH does not contain XELB_LISPDIR" >&2
        echo "EMACSLOADPATH=${EMACSLOADPATH:-}" >&2
        exit 1
        ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
EMACS_BIN=${EMACS:-emacs}
LOG="$SCRIPT_DIR/test_xelb.log"
"$EMACS_BIN" -Q --batch -L "$XELB_LISPDIR" -l "$SCRIPT_DIR/test_xelb.el" > "$LOG" 2>&1
EMU_STATUS=$?
if [ $EMU_STATUS -ne 0 ]; then
    echo "Emacs batch functional test failed (exit $EMU_STATUS), log:" >&2
    tail -n 30 "$LOG" >&2
    exit 1
fi

python3 - "$LOG" <<'EOF'
import json
import re
import sys

with open(sys.argv[1], encoding="utf-8", errors="replace") as handle:
    text = handle.read()
match = re.search(r"XELB-RESULT: passed=(\d+) total=(\d+)", text)
if not match:
    print("XELB-RESULT line missing from Emacs batch log", file=sys.stderr)
    sys.exit(1)
passed, total = int(match.group(1)), int(match.group(2))
if passed != total or total != 10:
    print(f"unexpected consumer counts passed={passed} total={total}", file=sys.stderr)
    sys.exit(1)
marker = {
    "executed": True,
    "passed": True,
    "command": "sh test_xelb.sh -> emacs -Q --batch -L $XELB_LISPDIR -l test_xelb.el",
    "discovered": total,
    "passedCount": passed,
}
print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(marker)}")
EOF

printf '%s\n' "xelb Emacs batch load validation OK"
