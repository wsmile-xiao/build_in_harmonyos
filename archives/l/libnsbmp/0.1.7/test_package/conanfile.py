import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.test_requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d compliance: explicit self.run() of the built test binary.
        # cmake.test() would also work but the CI L0 gate greps for self.run().
        exe = os.path.join(self.cpp.build.bindirs[0], "test_package")
        self.run(f'"{exe}"', env="conanrun")
