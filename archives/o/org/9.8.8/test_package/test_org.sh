#!/usr/bin/env sh
set -eu
if (set -o pipefail) 2>/dev/null; then
    set -o pipefail
fi

if [ -z "${ORG_LISPDIR:-}" ]; then
    echo "ORG_LISPDIR is not set" >&2
    exit 1
fi

if [ ! -f "$ORG_LISPDIR/org.el" ]; then
    echo "org.el is missing from ORG_LISPDIR: $ORG_LISPDIR" >&2
    exit 1
fi

if [ ! -f "$ORG_LISPDIR/ol.el" ]; then
    echo "ol.el is missing from ORG_LISPDIR: $ORG_LISPDIR" >&2
    exit 1
fi

case ":${EMACSLOADPATH:-}:" in
    *":$ORG_LISPDIR:"*) ;;
    *)
        echo "EMACSLOADPATH does not contain ORG_LISPDIR" >&2
        echo "EMACSLOADPATH=${EMACSLOADPATH:-}" >&2
        exit 1
        ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
EMACS_BIN=${EMACS:-emacs}
"$EMACS_BIN" -Q --batch -L "$ORG_LISPDIR" -l "$SCRIPT_DIR/test_org.el"
printf '%s\n' "org Emacs batch load validation OK"
