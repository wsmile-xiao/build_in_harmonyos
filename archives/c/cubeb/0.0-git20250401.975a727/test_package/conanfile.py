import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CubebTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindir, "test_cubeb")
        # On OHOS, libc++_shared.so is in /system/lib64
        # shell=True (default) allows env var prefix
        self.run(f"LD_LIBRARY_PATH=/system/lib64:$LD_LIBRARY_PATH \"{test_bin}\"")
