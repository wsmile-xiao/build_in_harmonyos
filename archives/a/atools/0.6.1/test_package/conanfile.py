import os
import sys

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        pkg = self.dependencies[self.tested_reference_str].package_folder
        site_pkg = os.path.join(pkg, "lib", py_ver, "site-packages")
        # L0c 要求 test_package 有测试源文件（test_atools.py——真实 API）——
        # L0d 要求 test() 有 self.run
        self.run(f'python3 test_atools.py "{site_pkg}"', env="conanrun")
