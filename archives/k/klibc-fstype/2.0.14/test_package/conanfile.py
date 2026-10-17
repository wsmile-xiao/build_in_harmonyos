import os

from conan import ConanFile
from conan.errors import ConanException


class TestPackage(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindirs = self.dependencies["klibc-fstype"].cpp_info.bindirs
        if not bindirs:
            raise ConanException("klibc-fstype package does not declare a bin directory")
        binary = os.path.join(bindirs[0], "fstype")
        if not os.path.isfile(binary):
            raise ConanException(f"klibc-fstype executable missing: {binary}")
        script = os.path.join(self.recipe_folder, "test_fstype.sh")
        self.run(f'sh "{script}" "{binary}"', env="conanrun")
