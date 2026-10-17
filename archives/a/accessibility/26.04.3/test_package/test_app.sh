#!/bin/sh
# Consumer smoke script for the packaged accessibility-inspector app.
# The real test() logic lives in conanfile.py (environment assembly +
# direct execution of bin/accessibilityinspector --version with the
# offscreen QPA platform); this file documents and mirrors that call so
# the check can also be reproduced manually on the device:
#
#   LD_LIBRARY_PATH=<dep pkg>/lib:... \
#   QT_QPA_PLATFORM=offscreen \
#       <pkg>/bin/accessibilityinspector --version
#
# Exit code: 0 when the application reports its version, non-zero else.
APP_BIN="$1"
if [ -z "$APP_BIN" ] || [ ! -x "$APP_BIN" ]; then
    echo "usage: $0 <path-to-accessibilityinspector>" >&2
    exit 2
fi
"$APP_BIN" --version
