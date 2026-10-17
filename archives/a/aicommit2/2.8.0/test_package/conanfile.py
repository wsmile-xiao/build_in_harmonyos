import os

from conan import ConanFile
from conan.tools.build import can_run


class Aicommit2TestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            package_folder = self.dependencies["aicommit2"].package_folder
            executable = os.path.join(package_folder, "bin", "aicommit2")
            self.run(f'sh test.sh "{executable}"', env="conanrun")
