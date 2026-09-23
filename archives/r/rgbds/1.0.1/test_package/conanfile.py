#!/usr/bin/env python3
"""Functional consumer test for rgbds (executable toolchain package)."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class RgbdsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # The OHOS profile represents the AtomCode real-device test runtime.
        if str(self.settings.os) == "OHOS" or can_run(self):
            default_shell = (
                "/data/service/hnp/bin/bash"
                if str(self.settings.os) == "OHOS"
                else "bash"
            )
            shell = os.environ.get("CONFIG_SHELL", default_shell)
            script = os.path.join(self.source_folder, "test_rgbds.sh")
            # R34: pass the packaged bin/ directory by absolute path so the
            # test genuinely depends on the package binaries (moving bin/ away
            # during the destructive negative test breaks this).
            pkg_folder = self.dependencies["rgbds"].package_folder
            bin_dir = os.path.join(pkg_folder, "bin")
            self.run(f'{shell} "{script}" "{bin_dir}"', env="conanrun")
