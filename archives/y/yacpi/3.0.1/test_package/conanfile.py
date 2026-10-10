#!/usr/bin/env python3
"""Consumer-side runtime test for the YACPI application package."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class YacpiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skipping YACPI runtime test.")
            return

        package = self.dependencies["yacpi"]
        binary = os.path.join(package.package_folder, "bin", "yacpi")
        test_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "test_yacpi_harmonyos.sh",
        )
        self.run(
            f"bash {shlex.quote(test_script)} {shlex.quote(binary)}",
            env="conanrun",
        )
