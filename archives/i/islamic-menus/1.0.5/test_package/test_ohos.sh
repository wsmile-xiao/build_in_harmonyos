#!/system/bin/sh
# Run the actual package consumer on HarmonyOS PC and verify the target runtime.
set -eu

TEST_BIN="${1:-}"
PKG_ROOT="${2:-}"
if [ -z "$TEST_BIN" ] || [ -z "$PKG_ROOT" ]; then
    echo "FAIL: usage: test_ohos.sh <consumer-binary> <package-root>" >&2
    exit 2
fi

ARCH="$(uname -m)"
[ "$ARCH" = "aarch64" ] || {
    echo "FAIL: expected HarmonyOS PC AArch64, got $ARCH" >&2
    exit 1
}
echo "PASS: running on AArch64 ($ARCH)"

KERNEL="$(uname -a)"
echo "$KERNEL" | grep -qi 'HongMeng' || {
    echo "FAIL: kernel does not identify as HarmonyOS HongMeng: $KERNEL" >&2
    exit 1
}
echo "PASS: HarmonyOS HongMeng kernel: $KERNEL"

[ -x /system/bin/sh ] || {
    echo "FAIL: HarmonyOS system shell is unavailable" >&2
    exit 1
}
BASH_BIN=/data/service/hnp/bin/bash
[ -x "$BASH_BIN" ] || {
    echo "FAIL: HNP bash is unavailable for the native consumer" >&2
    exit 1
}
echo "PASS: HarmonyOS system shell and HNP bash are available"

case ":${XDG_CONFIG_DIRS:-}:" in
    *":$PKG_ROOT/etc/xdg:"*) ;;
    *) echo "FAIL: Conan runtime did not expose package XDG_CONFIG_DIRS" >&2; exit 1 ;;
esac
case ":${XDG_DATA_DIRS:-}:" in
    *":$PKG_ROOT/share:"*) ;;
    *) echo "FAIL: Conan runtime did not expose package XDG_DATA_DIRS" >&2; exit 1 ;;
esac
echo "PASS: Conan runtime exposes this package through XDG_CONFIG_DIRS and XDG_DATA_DIRS"

# HarmonyOS system sh (mksh) does not directly launch ELF in this environment;
# run the AArch64 consumer with the device's supported HNP bash interpreter.
"$BASH_BIN" -c '"$1" "$2"' _ "$TEST_BIN" "$PKG_ROOT"
