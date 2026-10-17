import os
from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        # L0c 要求 test_package 有测试源文件——L0d 要求 self.run
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test_asncounter.sh {pkg}", env="conanrun")
