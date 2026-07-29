import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, cmake_layout


class QuazipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2")
        self.requires("zlib/1.3.1")

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            cmd = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(cmd, env="conanrun")
