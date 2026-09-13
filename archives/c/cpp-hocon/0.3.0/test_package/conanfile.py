import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class CppHoconTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Declare the boost pair as DIRECT requirements: the boost1.84
        # package uses a custom (empty) layout, and its component
        # includedirs do not resolve when the package is pulled in only
        # transitively through cpp-hocon. A direct require makes CMakeDeps
        # emit the full include paths for the consumer.
        self.requires("boost1.84/1.84.0")
        self.requires("boost1.84-thread/1.84.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        # Same cmake_file_name collision workaround as the main recipe.
        deps.set_property("boost1.84-thread", "cmake_file_name",
                          "hocon-boost-thread")
        deps.generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: actually exercise the packaged library (parse, resolve,
        # typed reads). Run natively when possible.
        if can_run(self):
            self.run(os.path.join(self.build_folder, "test_cpp_hocon"),
                     env="conanrun")
        else:
            self.output.info("cross-building: compile+link check only")
