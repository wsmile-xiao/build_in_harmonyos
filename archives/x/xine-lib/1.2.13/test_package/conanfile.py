import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class XinelibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # VirtualRunEnv exports XINE_PLUGIN_PATH (declared by the xine-lib recipe)
        # so the engine can dlopen its packaged plugins, plus the runtime paths.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_xine-lib"), env="conanrun")
