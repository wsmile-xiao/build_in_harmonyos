#!/usr/bin/env python3
"""Consumer test for bash-argsparse."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class BashArgsparseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        package = self.dependencies["bash-argsparse"].package_folder
        bash_package = self.dependencies["bash"].package_folder
        library = os.path.join(package, "share", "bash-argsparse", "argsparse.sh")
        bash = os.path.join(bash_package, "bin", "bash")
        test_script = os.path.join(self.recipe_folder, "test_argsparse.sh")

        env = Environment()
        env.define("BASH_ARGSPARSE_ROOT", os.path.dirname(library))
        with env.vars(self).apply():
            self.run(f'"{bash}" "{test_script}" "{library}"')
