#!/usr/bin/env python3
"""Consumer test for the packaged Wput command on native HarmonyOS."""

import os
import shlex
import sys

from conan import ConanFile


class WputTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["wput"].package_folder
        binary = os.path.join(package, "bin", "wput")
        if not os.path.isfile(binary):
            raise RuntimeError("wput executable is missing from the package")
        self.run(
            "%s test_wput.py %s" % (shlex.quote(sys.executable), shlex.quote(binary)),
            env="conanrun",
        )
