#!/usr/bin/env zsh
# Validate the packaged imenu-list Elisp with the published Emacs runtime.
set -euo pipefail

: "${IMENU_LIST_LISPDIR:?IMENU_LIST_LISPDIR is required}"
test -f "$IMENU_LIST_LISPDIR/imenu-list.el"
test -f "$IMENU_LIST_LISPDIR/imenu-list.elc"

case ":${EMACSLOADPATH:-}:" in
    *":$IMENU_LIST_LISPDIR:"*) ;;
    *)
        echo "EMACSLOADPATH does not contain IMENU_LIST_LISPDIR" >&2
        exit 1
        ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
EMACS_BIN=${EMACS:-emacs}
"$EMACS_BIN" -Q --batch -L "$IMENU_LIST_LISPDIR" -l "$SCRIPT_DIR/test_imenu_list.el"
printf '%s\n' "imenu-list 0.9 consumer validation: 8/8 PASS"
