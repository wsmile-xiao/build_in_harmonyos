import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class GettextTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        catalog = os.path.join(
            self.build_folder,
            "locale",
            "zh_CN",
            "LC_MESSAGES",
            "gettext-conan-test.mo",
        )
        generator = os.path.join(self.recipe_folder, "create_mo.py")
        self.run(f'"{sys.executable}" "{generator}" "{catalog}"')
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindir, "test_gettext")
            locale_directory = os.path.join(self.build_folder, "locale")
            self.run(f'"{executable}" "{locale_directory}"', env="conanrun")
