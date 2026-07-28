"""Conan test_package — 验证 highs 库可正常使用"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class HighsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the compiled test binary to verify HiGHS API works
        bin_path = os.path.join(self.build_folder, "test_highs")
        self.run(bin_path, env="conanrun")
