#!/usr/bin/env python3
"""Functional consumer test for lxsplit 0.2.4.

Verifies the real split → join round-trip:
  1. create a small file
  2. split it with the packaged lxsplit
  3. join the pieces back with the packaged lxsplit
  4. cmp the recovered file against the original
The binary is passed to the script by absolute path so the test genuinely
depends on the Conan package (R34: moving bin/ away breaks it).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class LxsplitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # The OHOS profile is the real-device test runtime; keep the test
        # executable when L1e invokes conan test with only its host profile.
        if str(self.settings.os) == "OHOS" or can_run(self):
            # Resolve bash via PATH (the OHOS profile's buildenv provides it).
            # CONFIG_SHELL, when set, takes precedence — same convention the
            # lavat test_package uses.
            shell = os.environ.get("CONFIG_SHELL", "bash")
            script = os.path.join(self.source_folder, "test_lxsplit.sh")
            # R34: pass the packaged lxsplit by absolute path so the test
            # genuinely depends on the package binary (moving bin/ away
            # during the destructive negative test breaks this).
            pkg_folder = self.dependencies["lxsplit"].package_folder
            bin_path = os.path.join(pkg_folder, "bin", "lxsplit")
            self.run(f'{shell} "{script}" "{bin_path}"', env="conanrun")
