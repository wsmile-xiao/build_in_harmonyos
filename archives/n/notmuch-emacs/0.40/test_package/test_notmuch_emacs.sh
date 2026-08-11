#!/usr/bin/env sh
set -eu
if (set -o pipefail) 2>/dev/null; then
    set -o pipefail
fi

if [ -z "${NOTMUCH_EMACS_LISPDIR:-}" ]; then
    echo "NOTMUCH_EMACS_LISPDIR is not set" >&2
    exit 1
fi

if [ ! -f "$NOTMUCH_EMACS_LISPDIR/notmuch.el" ]; then
    echo "notmuch.el is missing from NOTMUCH_EMACS_LISPDIR: $NOTMUCH_EMACS_LISPDIR" >&2
    exit 1
fi

if [ ! -f "$NOTMUCH_EMACS_LISPDIR/notmuch-version.el" ]; then
    echo "notmuch-version.el is missing from NOTMUCH_EMACS_LISPDIR: $NOTMUCH_EMACS_LISPDIR" >&2
    exit 1
fi

case ":${EMACSLOADPATH:-}:" in
    *":$NOTMUCH_EMACS_LISPDIR:"*) ;;
    *)
        echo "EMACSLOADPATH does not contain NOTMUCH_EMACS_LISPDIR" >&2
        echo "EMACSLOADPATH=${EMACSLOADPATH:-}" >&2
        exit 1
        ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
EMACS_BIN=${EMACS:-emacs}
"$EMACS_BIN" -Q --batch -L "$NOTMUCH_EMACS_LISPDIR" -l "$SCRIPT_DIR/test_notmuch_emacs.el"
printf '%s\n' "notmuch-emacs batch load validation OK"
