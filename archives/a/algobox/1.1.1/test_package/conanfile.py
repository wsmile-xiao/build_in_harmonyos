#!/usr/bin/env python3
"""Consumer smoke test for the AlgoBox executable package."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class AlgoboxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        package = self.dependencies["algobox"].package_folder
        executable = os.path.join(package, "bin", "algobox")
        shell = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        self.run(
            "{} test.sh {}".format(shlex.quote(shell), shlex.quote(executable)),
            env="conanrun",
        )
