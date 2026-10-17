import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KtoblzcheckTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            pkg = self.dependencies["ktoblzcheck"].package_folder
            bankdata = os.path.join(
                pkg, "share", "ktoblzcheck", "bankdata_20200420.txt"
            )
            bin_path = os.path.join(self.cpp.build.bindir, "test_ktoblzcheck")
            self.run(f"{bin_path} {bankdata}", env="conanrun")
