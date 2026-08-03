import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class PakoTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        package_folder = shlex.quote(self.dependencies["pako"].package_folder)
        self.run(f"CONAN_PACKAGE_FOLDER_pako={package_folder} sh test.sh", env="conanrun")
