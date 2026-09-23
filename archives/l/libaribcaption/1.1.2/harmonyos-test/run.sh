#!/bin/sh
# harmonyos-test runner — libaribcaption 1.1.2 on HarmonyOS PC (aarch64)
#
# Reproducible entry: configures + builds the harmonyos test against the
# conan-built package, then runs it natively, and performs the ELF-side
# checks (DT_SONAME / DT_NEEDED / .codesign presence) with readelf.
#
# Usage (from archives/l/libaribcaption/1.1.2/harmonyos-test):
#   ./run.sh <package_prefix> [<conan_toolchain.cmake>]
#
#   <package_prefix>  — the libaribcaption package folder (contains
#                       include/ and lib/) produced by conan create
#                       (shared package)
#   <conan_toolchain.cmake> — optional, the toolchain used to cross-compile
#                       for ohos-aarch64; when omitted the native compiler
#                       is used.
#
# Runtime closure: the dependency libraries are copied next to the test
# binary, named by their SONAME, and signed with binary-sign-tool — the
# musl loader on HarmonyOS only maps signed libraries.

set -eu

PREFIX="${1:?usage: run.sh <package_prefix> [<conan_toolchain.cmake>]}"
TOOLCHAIN="${2:-}"

HERE=$(cd "$(dirname "$0")" && pwd)
BUILD="$HERE/build"

CMAKE_ARGS="-DCMAKE_PREFIX_PATH=$PREFIX -DCMAKE_BUILD_TYPE=Release"
if [ -n "$TOOLCHAIN" ]; then
    CMAKE_ARGS="$CMAKE_ARGS -DCMAKE_TOOLCHAIN_FILE=$TOOLCHAIN"
fi

cmake -S "$HERE" -B "$BUILD" $CMAKE_ARGS
cmake --build "$BUILD" -j4 2>/dev/null || cmake --build "$BUILD"

TESTBIN="$BUILD/harmonyos_libaribcaption_test"
LIBDIR=$(dirname "$(ls -1 "$PREFIX"/lib*/libaribcaption.so 2>/dev/null | head -1)" 2>/dev/null || echo "$PREFIX/lib")

# --- ELF checks -----------------------------------------------------
READELF="${READELF:-readelf}"
SIGNTOOL="${SIGNTOOL:-$HOME/usr/local/bin/binary-sign-tool}"

echo "== ELF checks: $LIBDIR/libaribcaption.so =="
# 1) AArch64 machine check
MACHINE=$($READELF -h "$LIBDIR/libaribcaption.so" | sed -n 's/.*Machine: *//p' | head -1)
case "$MACHINE" in
    *AArch64*) echo "[ok] ELF machine = $MACHINE";;
    *) echo "[fail] ELF machine is $MACHINE, expected AArch64"; exit 1;;
esac

# 2) DT_SONAME must exist and be the bare relative name
SONAME=$($READELF -d "$LIBDIR/libaribcaption.so" | sed -n 's/.*Library soname: \[\(.*\)\]/\1/p' | head -1)
if [ -z "$SONAME" ]; then
    echo "[fail] libaribcaption.so has no DT_SONAME"; exit 1
fi
case "$SONAME" in
    */*) echo "[fail] DT_SONAME is an absolute path: $SONAME"; exit 1;;
    *)   echo "[ok] DT_SONAME = $SONAME (relative)";;
esac

# 3) DT_NEEDED of the test binary must reference libaribcaption + renderer deps
echo "== ELF checks: $TESTBIN =="
NEEDED=$($READELF -d "$TESTBIN" | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p')
echo "$NEEDED" | sed 's/^/    NEEDED /'
case "$NEEDED" in
    *libaribcaption.so*) echo "[ok] DT_NEEDED contains libaribcaption.so";;
    *) echo "[fail] DT_NEEDED missing libaribcaption.so"; exit 1;;
esac
case "$NEEDED" in
    *libc.so*|*ld-musl*) echo "[ok] NEEDED closure uses musl libc";;
    *) echo "[warn] no libc.so in NEEDED (static libc?)";;
esac

# 4) .codesign section presence (sign the artifacts first, then verify)
if [ -x "$SIGNTOOL" ] || command -v "$SIGNTOOL" >/dev/null 2>&1; then
    for f in "$TESTBIN" "$LIBDIR/libaribcaption.so"; do
        if "$SIGNTOOL" sign -inFile "$f" -outFile "$f.signed" -selfSign 1; then
            mv "$f.signed" "$f"
            chmod +x "$f"
        else
            echo "[fail] binary-sign-tool failed for $f"; exit 1
        fi
    done
    if $READELF -S "$LIBDIR/libaribcaption.so" 2>/dev/null | grep -q "\.codesign"; then
        echo "[ok] .codesign section present in libaribcaption.so"
    else
        echo "[fail] .codesign section missing in libaribcaption.so"; exit 1
    fi
    if $READELF -S "$TESTBIN" 2>/dev/null | grep -q "\.codesign"; then
        echo "[ok] .codesign section present in test binary"
    else
        echo "[fail] .codesign section missing in test binary"; exit 1
    fi
else
    echo "[warn] binary-sign-tool not found; skipping .codesign check"
fi

# --- Runtime closure --------------------------------------------------
# Copy every DT_NEEDED dependency (recursively) into a closure dir, named
# by SONAME, and sign it — mirroring what the recipe's build() does.
RUNLIBS="$BUILD/runlibs"
mkdir -p "$RUNLIBS"

collect_lib() {
    # $1 = library soname
    [ -f "$RUNLIBS/$1" ] && return 0
    for d in "$LIBDIR" $EXTRA_LIBDIRS; do
        for cand in "$d/$1" "$d/${1%.*}" "$d/${1%%.*}.so"; do
            if [ -f "$cand" ]; then
                cp -L "$cand" "$RUNLIBS/$1"
                if [ -x "$SIGNTOOL" ] || command -v "$SIGNTOOL" >/dev/null 2>&1; then
                    "$SIGNTOOL" sign -inFile "$RUNLIBS/$1" -outFile "$RUNLIBS/$1.s" -selfSign 1 >/dev/null
                    mv "$RUNLIBS/$1.s" "$RUNLIBS/$1"
                    chmod +x "$RUNLIBS/$1"
                fi
                # recurse into its NEEDED
                for sub in $($READELF -d "$RUNLIBS/$1" | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p'); do
                    case "$sub" in
                        libc.so*|ld-musl*|libc++*.so|libm.so*) ;; # system libs
                        *) collect_lib "$sub" ;;
                    esac
                done
                return 0
            fi
        done
    done
    echo "[warn] dependency $1 not found in LIBDIR/EXTRA_LIBDIRS"
}

# Dependency libs live in the conan cache; let the caller extend the search
EXTRA_LIBDIRS="${EXTRA_LIBDIRS:-}"
collect_lib "$SONAME"

# --- Runtime ---------------------------------------------------------
export LD_LIBRARY_PATH="$RUNLIBS"
"$TESTBIN"
echo "== harmonyos-test PASSED =="
