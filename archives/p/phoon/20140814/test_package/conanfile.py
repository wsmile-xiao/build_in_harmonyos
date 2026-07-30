import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PhoonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Direct smoke test: run phoon and check it produces output
        self.run("phoon", env="conanrun")
        # Build-time test: run the C test that verifies phoon output
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_phoon")
        self.run(f"{test_bin}", env="conanrun")
