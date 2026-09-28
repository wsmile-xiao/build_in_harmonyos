import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_tinydb.py")
            self.run(f'"{sys.executable}" "{test_script}"',
                     env="conanrun")