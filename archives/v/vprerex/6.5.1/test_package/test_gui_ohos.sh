#!/usr/bin/env bash
# test_package/test_gui_ohos.sh — HarmonyOS-specific *real GUI* test for the
# packaged vprerex binary.
#
# Unlike test.sh (which drives only the poppler-qt5 shim through the
# non-GUI --check-pdf entry point), this test exercises the real graphical
# application path on the OHOS target:
#   * QApplication construction on the offscreen QPA platform plugin
#     (plugins/platforms/libqoffscreen.so of qt5-qtbase), i.e. the Qt platform
#     plugin actually loads and initialises on HarmonyOS;
#   * the real MainWindow (ui_window.h) and DocumentWidget (QLabel) chain;
#   * loading a PDF through the poppler-qt5 shim inside that widget;
#   * a real Qt event-loop turn and a real widget-tree render
#     (QWidget::grab() -> pixels), which is only possible when Qt5 Gui/Widgets
#     and the platform plugin are fully working on the target.
#
# No display is required (offscreen QPA); exit code 0 means the whole GUI stack
# worked on the device.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
export QT_QPA_PLATFORM=offscreen

echo "[1/1] vprerex --check-gui selftest.pdf (QApplication + Window + shim + real render)"
out="$(vprerex --check-gui "${HERE}/selftest.pdf" 2>&1)"
printf '%s\n' "$out"

printf '%s\n' "$out" | grep -q "vprerex-gui: pages=1" || {
    echo "FAIL: the real window did not load the PDF (page count)" >&2
    exit 1
}
printf '%s\n' "$out" | grep -qE "vprerex-gui: ok pages=1 grab=[1-9][0-9]*x[1-9][0-9]* nonwhite=[1-9][0-9]*" || {
    echo "FAIL: widget-tree grab produced no rendered content" >&2
    exit 1
}

echo "OK: vprerex real GUI path (QApplication offscreen QPA + MainWindow + DocumentWidget + poppler-qt5 shim + render) passed on OHOS"
