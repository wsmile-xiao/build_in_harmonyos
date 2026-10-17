
#!/bin/sh

set -eu



PKG="$1"

APP="$PKG/share/acf/app/openntpd"



if [ ! -d "$APP" ]; then

    echo "FAIL: app directory missing: $APP"

    exit 1

fi



FILES="

openntpd-config-html.lsp

openntpd-controller.lua

openntpd-details-html.lsp

openntpd-expert-html.lsp

openntpd-logfile-html.lsp

openntpd-model.lua

openntpd-status-html.lsp

openntpd.menu

openntpd.roles

"



for f in $FILES; do

    if [ ! -e "$APP/$f" ] && [ ! -L "$APP/$f" ]; then

        echo "FAIL: missing $f"

        exit 1

    fi

    echo "PASS: $f exists"

done



if [ ! -L "$APP/openntpd-expert-html.lsp" ]; then

    echo "FAIL: openntpd-expert-html.lsp is not a symlink"

    exit 1

fi



if [ ! -L "$APP/openntpd-logfile-html.lsp" ]; then

    echo "FAIL: openntpd-logfile-html.lsp is not a symlink"

    exit 1

fi



if [ ! -L "$APP/openntpd-status-html.lsp" ]; then

    echo "FAIL: openntpd-status-html.lsp is not a symlink"

    exit 1

fi



echo "PASS: upstream dangling symlinks preserved"
