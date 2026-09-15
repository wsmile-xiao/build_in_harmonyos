#!/bin/sh
# Consumer smoke script for the packaged alligator application.
# The real test() logic lives in conanfile.py (environment assembly +
# direct execution of bin/alligator --self-test with the offscreen QPA
# platform); this file documents and mirrors that call so the check can
# also be reproduced manually on the device:
#
#   LD_LIBRARY_PATH=<dep pkg>/lib:... \
#   QML2_IMPORT_PATH=<dep pkg>/lib/qml:...:<pkg>/bin \
#   QT_QPA_PLATFORM=offscreen \
#       <pkg>/bin/alligator --self-test
#
# --self-test is the upstream automated-testing entry point
# (autotests/CMakeLists.txt registers it as alligator-self-test): it
# loads the full Kirigami QML UI (Main.qml + org.kde.alligator models
# backed by SQLite) and quits after 250 ms. Exit code: 0 when the QML
# engine loads the application cleanly, non-zero else (engine failure
# to load Main.qml returns -1).
APP_BIN="$1"
if [ -z "$APP_BIN" ] || [ ! -x "$APP_BIN" ]; then
    echo "usage: $0 <path-to-alligator>" >&2
    exit 2
fi
"$APP_BIN" --self-test
