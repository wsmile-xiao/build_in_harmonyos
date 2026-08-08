import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class GtkMacIntegrationTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        glib_folder = self.dependencies["glib"].package_folder
        tc = CMakeToolchain(self)
        tc.variables["GLIB_INCLUDE_DIR"] = os.path.join(
            glib_folder, "include", "glib-2.0"
        ).replace("\\", "/")
        tc.variables["GLIB_CONFIG_INCLUDE_DIR"] = os.path.join(
            glib_folder, "lib", "glib-2.0", "include"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run("./test_package", env="conanrun")
