import os

from conan import ConanFile
from conan.tools.build import can_run


class PcharTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            binary = os.path.join(self.dependencies["pchar"].package_folder, "sbin", "pchar")
            self.run(f'"{binary}" -h', env="conanrun")
