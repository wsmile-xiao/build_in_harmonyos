import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["fatal"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_fatal.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}" '
                     f'"{self.build_folder}"',
                     env="conanrun")
