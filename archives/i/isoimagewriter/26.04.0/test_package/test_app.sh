#!/bin/sh
# Consumer smoke script for the packaged isoimagewriter application.
# Manual reproduction helper — the executed test lives in conanfile.py.
set -eu
#
# The real test() logic lives in conanfile.py (runtime environment assembly +
# direct execution of bin/isoimagewriter with the offscreen QPA platform);
# this script documents and mirrors those calls so the check can also be
# reproduced manually on the device:
#
#   LD_LIBRARY_PATH=<dep pkg>/lib:<dep pkg>/bin:...:/system/lib64 \
#   QT_PLUGIN_PATH=<dep pkg>/plugins:... \
#   QT_QPA_PLATFORM=offscreen \
#       <pkg>/bin/isoimagewriter --version
#   ...                              --help
#
# Upstream ships no test suite (no autotests/ directory, no
# enable_testing()/add_test()), so the packaged executable itself is the
# subject under test.  Constructing QApplication loads the offscreen QPA
# plugin and the whole Qt6/KF6 link closure; KAboutData then prints the
# version and exits 0.  A non-zero exit means the application cannot start.
APP_BIN="$1"
if [ -z "$APP_BIN" ] || [ ! -x "$APP_BIN" ]; then
    echo "usage: $0 <path-to-isoimagewriter>" >&2
    exit 2
fi
"$APP_BIN" --version || exit 1
"$APP_BIN" --help || exit 1
