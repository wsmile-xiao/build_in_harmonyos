#!/usr/bin/env sh
set -eu
if (set -o pipefail) 2>/dev/null; then
    set -o pipefail
fi

if [ -z "${COMPAT_LISPDIR:-}" ]; then
    echo "COMPAT_LISPDIR is not set" >&2
    exit 1
fi

if [ ! -f "$COMPAT_LISPDIR/compat.el" ]; then
    echo "compat.el is missing from COMPAT_LISPDIR: $COMPAT_LISPDIR" >&2
    exit 1
fi

case ":${EMACSLOADPATH:-}:" in
    *":$COMPAT_LISPDIR:"*) ;;
    *)
        echo "EMACSLOADPATH does not contain COMPAT_LISPDIR" >&2
        echo "EMACSLOADPATH=${EMACSLOADPATH:-}" >&2
        exit 1
        ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
EMACS_BIN=${EMACS:-emacs}
"$EMACS_BIN" -Q --batch -l "$SCRIPT_DIR/test_compat.el"
printf '%s\n' "compat Emacs batch load validation OK"
