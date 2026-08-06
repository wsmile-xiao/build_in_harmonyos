#!/usr/bin/env python3
"""Conan test_package for alpine-chroot-install 0.14.0 — Shell script static smoke test.

The installed artifact is a single POSIX shell script. This test executes
test_smoke.sh against the packaged artifact to verify:
  1. the script is present and executable in the package bin/,
  2. `sh -n` syntax check passes,
  3. the script is a POSIX shell script (shebang, no binary payload),
  4. LICENSE is packaged under licenses/.

The installed script itself is NOT executed: on OHOS `id -u` reports
"bad uid", which defeats the script's root check and would start a real
chroot install with network side effects.
"""
import os
import shutil

from conan import ConanFile


class AlpineChrootInstallTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        test_script = os.path.join(self.source_folder, "test_smoke.sh")
        if not os.path.isfile(test_script):
            raise Exception(f"test source not found: {test_script}")

        sh = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "/system/bin/sh"

        # Execute the test source: static assertions on the packaged artifact
        self.run(
            f'"{sh}" "{test_script}" "{pkg_folder}" "{sh}"',
            env="conanrun",
        )
