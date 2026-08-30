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
            pkg = self.dependencies["cycler"].package_folder
            py_paths = [os.path.join(pkg, "lib", "python3.12",
                                     "site-packages")]
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_cycler.py")
            self.run(
                f'PYTHONPATH="{os.pathsep.join(py_paths)}" '
                f'{sys.executable} "{test_script}" "{pkg}"',
                env="conanrun")
