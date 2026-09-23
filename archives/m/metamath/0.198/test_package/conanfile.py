#!/usr/bin/env python3
"""Consumer test for the packaged Metamath executable."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class MetamathTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info(
                "Skipping runtime test because the host cannot run the target binary"
            )
            return

        package_folder = self.dependencies["metamath"].package_folder
        binary = os.path.join(package_folder, "bin", "metamath")
        script = os.path.join(self.source_folder, "test_metamath.sh")
        database = os.path.join(self.source_folder, "minimal.mm")
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f'"{shell}" "{script}" "{binary}" "{database}"',
            env="conanrun",
        )
