from conan import ConanFile
from conan.tools.build import can_run
import os
import sys


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            package = self.dependencies["debconf"].package_folder
            script = os.path.join(os.path.dirname(__file__), "test_debconf.py")
            self.run(f'{sys.executable} "{script}" "{package}"',
                     env="conanrun")
