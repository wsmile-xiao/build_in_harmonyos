#!/usr/bin/env python3
"""Consumer test for the packaged ACPICA iASL utility."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class AcpicaUnixTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_iasl.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            package_folder = self.dependencies["acpica-unix"].package_folder
            iasl = os.path.join(package_folder, "bin", "iasl")
            script = os.path.join(self.source_folder, "test_iasl.sh")
            self.run(
                "sh {} {}".format(shlex.quote(script), shlex.quote(iasl)),
                env="conanrun",
            )
