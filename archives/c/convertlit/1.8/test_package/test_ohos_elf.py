#!/usr/bin/env python3
"""Verify that the OHOS package contains the expected target executable."""

import pathlib
import sys


executable = pathlib.Path(sys.argv[1])
header = executable.read_bytes()[:20]

# HarmonyOS PC armv8 packages must contain a little-endian ELF64 AArch64
# executable.  This catches accidental host binaries and wrong-architecture
# packages while inspecting the real packaged clit artifact.
is_ohos_target = (
    len(header) == 20
    and header[:4] == b"\x7fELF"
    and header[4] == 2
    and header[5] == 1
    and int.from_bytes(header[16:18], "little") in (2, 3)
    and int.from_bytes(header[18:20], "little") == 183
)
if not is_ohos_target:
    raise SystemExit(
        f"expected ELF64 little-endian AArch64 clit, got header {header.hex()}"
    )

print("HarmonyOS ELF64/AArch64 package identity test passed")
