import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class YafcTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if can_run(self):
            binary = os.path.join(self.dependencies["yafc"].package_folder, "bin", "yafc")
            self.run(shlex.join([sys.executable, os.path.join(self.source_folder, "test.py"), binary]),
                     env="conanrun", cwd=self.build_folder)
