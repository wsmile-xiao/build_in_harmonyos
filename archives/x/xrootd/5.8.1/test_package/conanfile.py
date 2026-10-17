from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Real client-API exercise: XrdCl URL parsing plus a local-to-local
        # copy through the XrdCl copy machinery (see test_xrootd.cpp).
        bin_path = os.path.join(self.cpp.build.bindir, "test_xrootd")
        self.run(f'"{bin_path}"', env="conanrun")
