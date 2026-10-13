#!/bin/bash
# Build the DAYU200 consumer e2e test binary (`mesa_device_e2e`) from consumer.c.
#
# The device has no pre-installed mesa, so the payload ships mesa's shared
# libraries next to the executable and the binary carries RUNPATH=$ORIGIN.
#
# NOTE: device_runner.sh uploads only TOP-LEVEL files of the payload directory,
# so keep everything flat (no subdirectories) or the libraries will not be pushed.
#
# The binary itself is deliberately NOT committed (project file rule: "PR 中禁止
# 包含预编译的 .so/.a/二进制文件").  Its identity is pinned by the SHA-256 and
# byte count recorded in README.md; rebuild here and compare to verify.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
out="${1:-$here}"
sdk="${OHOS_SDK:-/root/ohpc/sdk/ohos-6.0/native}"
clang="$sdk/llvm/bin/aarch64-unknown-linux-ohos-clang"
sysroot="$sdk/sysroot"

# --- locate the mesa package produced by `conan create` -----------------------
# Accept an explicit override, else take the newest matching conan package dir.
pkg="${MESA_PKG:-}"
if [ -z "$pkg" ]; then
    pkg="$(ls -dt /root/.conan2/p/b/mesa*/p 2>/dev/null | head -1 || true)"
fi
if [ -z "$pkg" ] || [ ! -d "$pkg/include" ]; then
    echo "ERROR: cannot locate the mesa package; set MESA_PKG=<path>" >&2
    echo "       (build it first with: conan create archives/m/mesa/26.1.5)" >&2
    exit 1
fi

# LLVM is a runtime dependency of libgallium (llvmpipe); ship it alongside.
llvm_lib="${LLVM_LIB:-}"
if [ -z "$llvm_lib" ]; then
    llvm_lib="$(ls -d /root/.conan2/p/llvm*/p/lib 2>/dev/null | head -1 || true)"
fi
if [ -z "$llvm_lib" ] || [ ! -d "$llvm_lib" ]; then
    echo "ERROR: cannot locate libLLVM; set LLVM_LIB=<dir>" >&2
    exit 1
fi

echo "mesa package : $pkg"
echo "llvm lib dir : $llvm_lib"
echo "output dir   : $out"

# --- compile ------------------------------------------------------------------
"$clang" --sysroot="$sysroot" --target=aarch64-linux-ohos \
    -I"$pkg/include" "$here/consumer.c" -o "$out/mesa_device_e2e" \
    -L"$pkg/lib" -lEGL -lGLESv2 \
    -Wl,-rpath,'$ORIGIN' -Wl,--enable-new-dtags

# --- stage the shared libraries flat, next to the executable ------------------
cp "$pkg/lib/libEGL.so.1.0.0"      "$out/"
cp "$pkg/lib/libGLESv2.so.2.0.0"   "$out/"
cp "$pkg/lib/libgallium-26.1.5.so" "$out/"
cp "$llvm_lib/libLLVM.so.20.1"     "$out/"
cp "$sdk/llvm/lib/aarch64-linux-ohos/libc++_shared.so" "$out/"

(cd "$out" && ln -sf libEGL.so.1.0.0    libEGL.so.1)
(cd "$out" && ln -sf libGLESv2.so.2.0.0 libGLESv2.so.2)
for f in libEGL.so.1.0.0 libGLESv2.so.2.0.0 libgallium-26.1.5.so; do
    patchelf --set-rpath '$ORIGIN' "$out/$f"
done

echo
echo "built: $out/mesa_device_e2e"
sha256sum "$out/mesa_device_e2e"
echo "compare the SHA-256 above with device-evidence/README.md"
