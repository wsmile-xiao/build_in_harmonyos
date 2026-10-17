#!/usr/bin/env bash
# Consumer validation for the packaged riece Emacs Lisp add-on.
set -eu

if [ -z "${RIECE_LISPDIR:-}" ]; then
    echo "RIECE_LISPDIR is not set" >&2
    exit 1
fi

if [ ! -f "$RIECE_LISPDIR/riece.el" ]; then
    echo "riece.el is missing from RIECE_LISPDIR: $RIECE_LISPDIR" >&2
    exit 1
fi

if [ ! -f "$RIECE_LISPDIR/riece.elc" ]; then
    echo "riece.elc is missing (module was not byte-compiled): $RIECE_LISPDIR" >&2
    exit 1
fi

case ":${EMACSLOADPATH:-}:" in
    *":$RIECE_LISPDIR:"*) ;;
    *)
        echo "EMACSLOADPATH does not contain RIECE_LISPDIR" >&2
        echo "EMACSLOADPATH=${EMACSLOADPATH:-}" >&2
        exit 1
        ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
EMACS_BIN=${EMACS:-emacs}
"$EMACS_BIN" -Q --batch -L "$RIECE_LISPDIR" -l "$SCRIPT_DIR/test_riece.el"
printf '%s\n' "riece Emacs batch load validation OK"
