import os

from conan import ConanFile
from conan.tools.build import can_run


class UglifycssTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            package_folder = self.dependencies["uglifycss"].package_folder
            executable = os.path.join(package_folder, "bin", "uglifycss")
            self.run(f'sh test.sh "{executable}"', env="conanrun")
