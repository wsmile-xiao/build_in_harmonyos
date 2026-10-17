#!/usr/bin/env python3
"""test_package for recoverdm 0.20 — consumer smoke + functional test.

recoverdm needs a damaged disk/image to do real recovery work, so upstream ships
**no automated test at all** (the bare Makefile has no `check`/`test` target and
the tarball contains no test programs — see MANIFEST.yml).

This test therefore executes the packaged binaries for real (R34):
  * `recoverdm -V` / `-h` and the documented no-argument exit code,
  * a genuine end-to-end recovery pass over a regular file
    (device type FILE = 1) asserting a byte-identical 4096-byte image,
  * `mergebad -h`, its "at least 2 images" guard (exit 10) and a genuine
    two-image merge driven by bad-block map files.

The raw-device / CD-ROM / DVD retry paths (types 10..19, -r, -s) stay uncovered:
they need damaged removable media or a root-owned loop device, which the
HarmonyOS PC build hosts do not provide. See notes.md "测试五维账本".
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class RecoverdmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS conan 2.29.1: can_run() takes the conanfile (measured 2026-09-25,
        # G2 failed with "TypeError: can_run() missing 1 required positional
        # argument: conanfile").
        if not can_run(self):
            return
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        bindirs = dep.cpp_info.bindirs or ["bin"]
        for name in ("recoverdm", "mergebad"):
            found = [
                os.path.join(pkg, d, name) for d in bindirs
            ] + [os.path.join(pkg, "bin", name)]
            binary = next((p for p in found if os.path.isfile(p)), None)
            if binary is None:
                raise Exception(
                    f"{name} missing from the package (looked in: {found})"
                )
        # OHOS: /system/bin/sh may not run ELF binaries reliably -> use bash.
        # The script relies on PATH from the conanrun environment for bin/.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
