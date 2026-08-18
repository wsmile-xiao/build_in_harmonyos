#!/usr/bin/env zsh
# Validate the packaged web-mode Elisp with the published Emacs runtime.
set -euo pipefail

: "${WEB_MODE_LISPDIR:?WEB_MODE_LISPDIR is required}"
test -f "$WEB_MODE_LISPDIR/web-mode.el"
test -f "$WEB_MODE_LISPDIR/web-mode.elc"

case ":${EMACSLOADPATH:-}:" in
    *":$WEB_MODE_LISPDIR:"*) ;;
    *)
        echo "EMACSLOADPATH does not contain WEB_MODE_LISPDIR" >&2
        exit 1
        ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
EMACS_BIN=${EMACS:-emacs}
"$EMACS_BIN" -Q --batch -L "$WEB_MODE_LISPDIR" -l "$SCRIPT_DIR/test_web_mode.el"
printf '%s\n' "web-mode 17.3.20 consumer validation: 8/8 PASS"
