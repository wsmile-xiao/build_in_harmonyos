#!/usr/bin/env python3
"""Teach LLVM's bundled config.guess about HarmonyOS (E007 class fix).

HarmonyOS PC reports ``UNAME_SYSTEM = HarmonyOS`` on an aarch64 kernel with a
Linux/syscall-compatible ABI and a musl libc.  The config.guess script shipped
inside llvm-19.1.5.src.tar.xz predates HarmonyOS and prints "unable to guess
system type" and exits non-zero.  LLVM's ``cmake/config-ix.cmake`` calls
``get_host_triple()`` unconditionally (LLVM_HOST_TRIPLE is an *output* of that
call, not an input), so the whole QBDI configure step aborts.

This script maps ``aarch64:HarmonyOS:*:*`` to the ``aarch64-unknown-linux-ohos``
vendor triple.  It is idempotent: if the mapping is already present it does
nothing.

Usage: ohos_config_guess_fix.py <path/to/config.guess>
"""
import sys

ANCHOR = 'case "${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}" in\n'

INSERT = (
    "    # HarmonyOS PC (OpenHarmony): UNAME_SYSTEM=HarmonyOS on an aarch64\n"
    "    # Linux-ABI (musl) kernel; map to the ohos vendor triple.\n"
    "    aarch64:HarmonyOS:*:*)\n"
    "\techo ${UNAME_MACHINE}-unknown-linux-ohos\n"
    "\texit ;;\n"
)


def main():
    if len(sys.argv) != 2:
        print("usage: ohos_config_guess_fix.py <config.guess>", file=sys.stderr)
        return 2
    path = sys.argv[1]
    with open(path, encoding="utf-8", errors="surrogateescape") as fh:
        src = fh.read()
    if "HarmonyOS" in src:
        print(f"ohos_config_guess_fix: already patched: {path}")
        return 0
    if ANCHOR not in src:
        print(f"ohos_config_guess_fix: anchor not found in {path}", file=sys.stderr)
        return 1
    with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
        fh.write(src.replace(ANCHOR, ANCHOR + INSERT, 1))
    print(f"ohos_config_guess_fix: patched {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
