#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the ant-phone executable
# Runs in conanrun env (PATH includes the installed bin/)
# ant-phone is a GTK2 GUI app; --version is handled before gtk_init()
# (see patches/0002), so it works headless — the stable smoke-test entry.
# Full telephony/ALSA/CAPI/GUI paths need a display and real hardware,
# and cannot run on the build host (OHOS has no display backend; E471).
set -eu

echo "[test] ant-phone --version"
ant-phone --version | grep -q "ANT 0.2.1"
echo "OK: --version returns ANT 0.2.1"
