#!/usr/bin/env python3
"""test_package for open-simh 3.12-3.

SIMH simulators are interactive console programs: they read SCP commands
from stdin and print a banner line "<machine> simulator V3.12-3".  The
smoke test pipes "show version + quit" into each of the 24 installed
simulators and asserts the banner, which proves the packaged binaries
start, initialise their device tables and execute the SCP command
interpreter on HarmonyOS PC (aarch64).
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class OpensimhTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    generators = "VirtualRunEnv"

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test_simh.py")
        self.run(
            f'"{sys.executable}" "{script}" "{bindir}"',
            env="conanrun",
        )
