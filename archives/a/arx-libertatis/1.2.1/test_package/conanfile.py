import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ArxLibertatisTestConan(ConanFile):
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
        # R34: Test must actually call the tested package's API
        # test_arx calls ArxIO_init(), ArxIO_getError(), ArxIO_unpack_alloc() etc.
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_arx")
        self.run(cmd, env="conanrun")
