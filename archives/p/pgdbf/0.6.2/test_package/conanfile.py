#!/usr/bin/env python3
"""Functional consumer test for pgdbf (converts a DBF fixture to SQL)."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class PgdbfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS profile runs on the real-device test runtime.
        if str(self.settings.os) == "OHOS" or can_run(self):
            default_shell = (
                "/data/service/hnp/bin/bash"
                if str(self.settings.os) == "OHOS"
                else "bash"
            )
            shell = os.environ.get("CONFIG_SHELL", default_shell)
            script = os.path.join(self.source_folder, "test_pgdbf.sh")
            # R34: pass the packaged pgdbf by absolute path so the test
            # genuinely depends on the package binary.
            pkg_folder = self.dependencies["pgdbf"].package_folder
            bin_path = os.path.join(pkg_folder, "bin", "pgdbf")
            self.run(f'{shell} "{script}" "{bin_path}"', env="conanrun")
