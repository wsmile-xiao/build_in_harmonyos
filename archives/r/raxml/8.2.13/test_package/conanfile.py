#!/usr/bin/env python3
"""raxml 8.2.13 test_package — consumer test.

Runs the packaged raxmlHPC CLI via test_raxml.py (version banner + minimal
PHYLIP GTRCAT ML search producing a result tree).
"""

import os
import shlex
import sys

from conan import ConanFile


class RaxmlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.recipe_folder, "test_raxml.py")
        self.run(f'{shlex.quote(sys.executable)} {shlex.quote(script)} {shlex.quote(package)}', env="conanrun")
