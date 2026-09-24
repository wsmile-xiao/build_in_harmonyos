import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NaclTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        # Compile happens under conanbuild; the binaries themselves are run under
        # conanrun so the OHOS loader paths apply.
        self.run(os.path.join(bindir, "test_nacl"), env="conanrun")
        self.run(os.path.join(bindir, "test_nacl_cpp"), env="conanrun")
