import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class CyrusSaslTestConan(ConanFile):
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
        if cross_building(self):
            self.output.info("cross-building: compile+link only")
            return
        exe = os.path.join(self.cpp.build.bindirs[0], "test_cyrus_sasl")
        # env="conanrun" applies the packed run environment: LD_LIBRARY_PATH
        # (libsasl2.so.3) and SASL_PATH (lib/sasl2 mechanism plugins).
        self.run(exe, env="conanrun")
