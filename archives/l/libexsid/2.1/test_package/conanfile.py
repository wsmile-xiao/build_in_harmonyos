from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibexsidTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        executable = self.cpp.build.bindirs[0] + "/test_libexsid"
        self.run(f'"{executable}"', env="conanrun")
