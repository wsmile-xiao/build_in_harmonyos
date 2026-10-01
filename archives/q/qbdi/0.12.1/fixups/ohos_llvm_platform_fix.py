#!/usr/bin/env python3
"""Make LLVM's platform detection accept HarmonyOS (UNIX-alike).

HarmonyOS PC has a Linux ABI (musl libc, `aarch64-unknown-linux-ohos`) but CMake
ships no ``Platform/HarmonyOS`` module, so the ``UNIX`` variable is not set.
LLVM's ``HandleLLVMOptions.cmake`` then falls through to
``MESSAGE(SEND_ERROR "Unable to determine platform")``.

This matters even when the main configure is told ``-DCMAKE_SYSTEM_NAME=Linux``,
because LLVM starts a **separate ``NATIVE`` sub-build** for TableGen (it believes
it is cross-compiling), and that nested configure re-autodetects the host as
HarmonyOS.

The fix treats HarmonyOS as the UNIX it is.  Idempotent.

Usage: ohos_llvm_platform_fix.py <llvm-src-root>
"""
import sys

REL = "cmake/modules/HandleLLVMOptions.cmake"
OLD = """elseif(FUCHSIA OR UNIX)
  set(LLVM_ON_WIN32 0)
  set(LLVM_ON_UNIX 1)
"""
NEW = """elseif(FUCHSIA OR UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
  # HarmonyOS PC has a Linux ABI (musl libc) but CMake ships no
  # Platform/HarmonyOS module, so UNIX is not set.  LLVM's NATIVE TableGen
  # sub-build re-autodetects the host as HarmonyOS and would otherwise abort
  # with "Unable to determine platform".
  set(LLVM_ON_WIN32 0)
  set(LLVM_ON_UNIX 1)
"""


def main():
    if len(sys.argv) != 2:
        print("usage: ohos_llvm_platform_fix.py <llvm-src-root>", file=sys.stderr)
        return 2
    path = sys.argv[1].rstrip("/") + "/" + REL
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    if 'CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"' in src:
        print(f"ohos_llvm_platform_fix: already patched: {path}")
        return 0
    if OLD not in src:
        print(f"ohos_llvm_platform_fix: anchor not found in {path}", file=sys.stderr)
        return 1
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src.replace(OLD, NEW, 1))
    print(f"ohos_llvm_platform_fix: patched {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
