import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class GtkplusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run via ctest, works under conanrun env
        cmake = CMake(self)
        cmake.test()
        # Also direct run with conanrun env to verify
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gtkplus")
        if os.path.isfile(bin_path):
            self.run(bin_path, env="conanrun")
