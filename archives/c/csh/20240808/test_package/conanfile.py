from __future__ import annotations

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class CshTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            self.output.warning("Skipping executable consumer test during cross-build")
            return

        package = self.dependencies["csh"]
        executable = os.path.join(package.package_folder, "bin", "csh")
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run(
            "sh %s %s" % (shlex.quote(script), shlex.quote(executable)),
            env="conanrun",
        )
