import os
from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["checkbashisms"]
        bin_path = os.path.join(str(dep.package_folder), "bin", "checkbashisms")
        self.run(f'"{bin_path}" --version', env="conanrun")
        self.run(f'"{bin_path}" --help', env="conanrun")