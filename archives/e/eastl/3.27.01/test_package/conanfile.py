import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class EastlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["EASTL_UPSTREAM_TEST_EXECUTABLE"] = os.path.join(
            self.dependencies["eastl"].package_folder, "bin", "EASTLTest")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(f'ctest --test-dir "{self.build_folder}" --output-on-failure',
                 env="conanrun")
