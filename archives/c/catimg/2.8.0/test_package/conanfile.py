from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CatimgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # R34: Verify catimg binary is installed and produces expected output
        self.run("catimg -h 2>&1 | grep -q Usage", env="conanrun")
