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
            deps = {str(d.ref.name): d.package_folder
                    for d in self.dependencies.values()}
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_moe.py")
            self.run(
                f'{sys.executable} "{test_script}" "{deps["moe"]}" '
                f'"{deps["ncurses"]}"',
                env="conanrun")
