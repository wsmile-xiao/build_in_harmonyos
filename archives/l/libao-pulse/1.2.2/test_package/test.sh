#!/data/service/hnp/bin/bash
# Consumer test driver for the published libao-pulse/1.2.2 package.
#
#   $1  consumer executable built by test_package/CMakeLists.txt
#   $2  package folder of the tested libao-pulse reference
#
# Covered here:
#   1. installed layout (libao.so.4, lib/ao/plugins-4/libpulse.so, ao.pc)
#   2. ELF contract of both artifacts, including the OHOS .codesign section
#      the loader requires
#   3. the plugin's DT_NEEDED pins the PulseAudio ABI it was linked against
#   4. libao really dlopens the plugin (the consumer asserts the pulse driver
#      registers itself)
#
# Runtime note 1: configure bakes the plugin directory into libao.so, and
# configure's prefix makes that /lib/ao/plugins-4, i.e. a read-only system
# location.  patches/0001 lets AO_PLUGIN_PATH redirect it, so both runs point
# libao at the tested package's own lib/ao/plugins-4.
#
# Runtime note 2: the OHOS loader maps signed objects only, and the published
# pulseaudio/17.0.1 libraries carry no .codesign section, so the second run
# below resolves libpulse.so.0 / libpulse-simple.so.0 against the signed
# platform client libraries.  The first run (plain conanrun environment)
# documents what happens with the artifact alone.
set -euo pipefail

EXE=$1
PKG=$2
DIR=$(dirname "$EXE")
ARTIFACT_LOG=$DIR/run-artifact.log

READELF=""
for candidate in llvm-readelf readelf /data/service/hnp/bin/llvm-readelf; do
    if command -v "$candidate" >/dev/null 2>&1; then
        READELF=$candidate
        break
    fi
done
[ -n "$READELF" ] || { echo "no readelf available"; exit 1; }

PASSED=0
FAILED=0
ok()  { echo "        [ok] $1"; PASSED=$((PASSED + 1)); }
bad() { echo "        [FAIL] $1"; FAILED=$((FAILED + 1)); }
check_contains() { # check_contains <label> <needle> <haystack>
    case "$3" in
        *"$2"*) ok "$1" ;;
        *)      bad "$1: '$2' not found" ;;
    esac
}
readelf_out() { # never abort under set -e: a missing artifact must be reported, not fatal
    "$READELF" "$@" 2>/dev/null || true
}

echo "[test] installed layout"
CORE=$(ls "$PKG"/lib/libao.so.4.* 2>/dev/null | head -1 || true)
PLUGIN=$PKG/lib/ao/plugins-4/libpulse.so
if [ -n "$CORE" ] && [ -f "$CORE" ]; then ok "core library $CORE"; else bad "libao.so.4 missing"; fi
if [ -f "$PLUGIN" ]; then ok "pulse plugin at lib/ao/plugins-4/libpulse.so"; else bad "plugin missing: $PLUGIN"; fi
if [ -f "$PKG/lib/pkgconfig/ao.pc" ]; then ok "ao.pc installed"; else bad "ao.pc missing"; fi

echo "[test] ELF contract"
check_contains "core is AArch64" "AArch64" "$(readelf_out -h "$CORE")"
check_contains "core SONAME" "libao.so.4" "$(readelf_out -d "$CORE")"
check_contains "core carries .codesign (OHOS loader)" ".codesign" "$(readelf_out -SW "$CORE")"
check_contains "plugin carries .codesign (OHOS loader)" ".codesign" "$(readelf_out -SW "$PLUGIN")"
PLUGIN_DYNAMIC=$(readelf_out -d "$PLUGIN")
check_contains "plugin needs libpulse-simple.so.0" "libpulse-simple.so.0" "$PLUGIN_DYNAMIC"
check_contains "plugin needs libpulse.so.0" "libpulse.so.0" "$PLUGIN_DYNAMIC"

echo "[test] runtime: plain run environment (pulseaudio artifact)"
PLUGIN_DIR=$PKG/lib/ao/plugins-4
if AO_PLUGIN_PATH="$PLUGIN_DIR" "$EXE" > "$ARTIFACT_LOG" 2>&1; then
    echo "        [info] plugin also loaded against the artifact libraries"
else
    echo "        [info] plugin could not resolve the artifact libraries"
    echo "        [info] (documented: the published .so files have no .codesign section)"
fi
sed -n '1,3p' "$ARTIFACT_LOG" | sed 's/^/        /'

echo "[test] runtime: signed platform PulseAudio client libraries"
SYS=$DIR/pulse-sys
mkdir -p "$SYS"
ln -sf /system/lib64/libpulseaudio.z.so "$SYS/libpulse.so.0"
ln -sf /system/lib64/libpulse-simple.z.so "$SYS/libpulse-simple.so.0"
if [ ! -f /system/lib64/libpulseaudio.z.so ] || [ ! -f /system/lib64/libpulse-simple.z.so ]; then
    bad "signed platform PulseAudio client libraries are missing"
else
    RUN_RC=0
    RUN_OUT=$(AO_PLUGIN_PATH="$PLUGIN_DIR" \
              LD_LIBRARY_PATH="$SYS:$PKG/lib" "$EXE" 2>&1) || RUN_RC=$?
    echo "$RUN_OUT" | sed 's/^/        /'
    if [ "$RUN_RC" -eq 0 ]; then
        ok "consumer exited 0 with AO_PLUGIN_PATH pointing at lib/ao/plugins-4"
    else
        bad "consumer exited $RUN_RC"
    fi
    check_contains "consumer summary" "consumer checks:" "$RUN_OUT"
    case "$RUN_OUT" in
        *FAIL*) bad "consumer reported a failing check" ;;
        *)      ok "consumer reported no failing check" ;;
    esac
fi

echo "[test] libao-pulse test_package: $PASSED passed, $FAILED failed"
[ "$FAILED" -eq 0 ]