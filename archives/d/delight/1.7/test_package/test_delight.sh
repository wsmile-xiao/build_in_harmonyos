#!/usr/bin/env sh
set -eu
if (set -o pipefail) 2>/dev/null; then
    set -o pipefail
fi

if [ -z "${DELIGHT_LISPDIR:-}" ]; then
    echo "DELIGHT_LISPDIR is not set" >&2
    exit 1
fi

for file in delight.el delight.elc; do
    if [ ! -f "$DELIGHT_LISPDIR/$file" ]; then
        echo "$file is missing from DELIGHT_LISPDIR: $DELIGHT_LISPDIR" >&2
        exit 1
    fi
done

case ":${EMACSLOADPATH:-}:" in
    *":$DELIGHT_LISPDIR:"*) ;;
    *)
        echo "EMACSLOADPATH does not contain DELIGHT_LISPDIR" >&2
        echo "EMACSLOADPATH=${EMACSLOADPATH:-}" >&2
        exit 1
        ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
EMACS_BIN=${EMACS:-emacs}
"$EMACS_BIN" -Q --batch -L "$DELIGHT_LISPDIR" -l "$SCRIPT_DIR/test_delight.el"
printf '%s\n' "delight Emacs batch load validation OK"
