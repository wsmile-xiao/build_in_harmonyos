#!/usr/bin/env sh
set -eu
if (set -o pipefail) 2>/dev/null; then
    set -o pipefail
fi

if [ -z "${OL_NOTMUCH_LISPDIR:-}" ]; then
    echo "OL_NOTMUCH_LISPDIR is not set" >&2
    exit 1
fi

for file in ol-notmuch.el ol-notmuch.elc ol-notmuch-autoloads.el; do
    if [ ! -f "$OL_NOTMUCH_LISPDIR/$file" ]; then
        echo "$file is missing from OL_NOTMUCH_LISPDIR: $OL_NOTMUCH_LISPDIR" >&2
        exit 1
    fi
done

for var in COMPAT_LISPDIR ORG_LISPDIR NOTMUCH_EMACS_LISPDIR; do
    eval "value=\${$var:-}"
    if [ -z "$value" ]; then
        echo "$var is not set" >&2
        exit 1
    fi
done

case ":${EMACSLOADPATH:-}:" in
    *":$OL_NOTMUCH_LISPDIR:"*) ;;
    *)
        echo "EMACSLOADPATH does not contain OL_NOTMUCH_LISPDIR" >&2
        echo "EMACSLOADPATH=${EMACSLOADPATH:-}" >&2
        exit 1
        ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
EMACS_BIN=${EMACS:-emacs}
"$EMACS_BIN" -Q --batch -L "$OL_NOTMUCH_LISPDIR" -l "$SCRIPT_DIR/test_ol_notmuch.el"
printf '%s\n' "ol-notmuch Emacs batch load validation OK"
