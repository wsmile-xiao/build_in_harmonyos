import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class LibprintsysTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Runs the real printcap parser end to end (10 assertions in test.c);
        # glib and tdb symbols are resolved through libprintsys' cpp_info.requires.
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_printcap")
            self.run(bin_path, env="conanrun")
