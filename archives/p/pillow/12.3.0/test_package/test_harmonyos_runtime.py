#!/usr/bin/env python3
"""HarmonyOS runtime checks for the packaged Pillow native extensions.

The consumer test imports the compiled extension from the Conan package and
verifies that it is an AArch64 OHOS ELF64 shared object.  When the CI worker
MAC domain refuses the shared object (see ``artifact_checks``) the packaged
artifacts are validated instead, so a broken package still fails the build.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import artifact_checks

if len(sys.argv) != 4:
    raise SystemExit(f"usage: {sys.argv[0]} <site-packages> <target-os> <target-arch>")

site_packages, target_os, target_arch = sys.argv[1:]
if target_os != "OHOS":
    raise AssertionError(f"expected the Conan OHOS target, got {target_os!r}")
if target_arch != "armv8":
    raise AssertionError(f"expected the OHOS aarch64 target, got {target_arch!r}")
if not os.path.isdir(site_packages):
    raise RuntimeError(f"Pillow site-packages directory is missing: {site_packages}")

sys.path.insert(0, site_packages)

for extension in artifact_checks.find_extensions(site_packages):
    if not os.access(extension, os.X_OK):
        # HMDFS folds the mode onto the group bits (knowledge/doc/E046.md),
        # so the exec bit is informational only and never a test failure.
        print(f"info: {os.path.basename(extension)} exposes no executable bit")

try:
    from PIL import _imaging
except ImportError as error:
    if not artifact_checks.is_mac_denial(error):
        raise
    # The CI worker MAC domain refuses the shared object, a real device loads it.
    print(f"WARNING: OHOS MAC denied the Pillow extension: {error}")
    print("WARNING: falling back to packaged ELF validation")
    artifact_checks.validate_packaged_extensions(site_packages)
    print("HarmonyOS Pillow native extension artifact validation passed")
    raise SystemExit(0)

extension = _imaging.__file__
artifact_checks.check_elf_header(extension)
artifact_checks.validate_packaged_extensions(site_packages)
print(f"HarmonyOS Pillow runtime loaded {os.path.basename(extension)}")
