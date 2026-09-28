import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibpurpleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("glib/2.84.0")
        self.requires("libxml2/2.15.3")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_libpurple")
        self.run(test_binary, env="conanrun")
