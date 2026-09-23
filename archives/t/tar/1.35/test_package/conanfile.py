import os
from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class TarTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        tar_bin = os.path.join(self.dependencies["tar"].package_folder, "bin", "tar")
        test_script = os.path.join(self.source_folder, "test_tar.sh")
        self.run(f'bash "{test_script}" "{tar_bin}" "{self.build_folder}"', env="conanrun")