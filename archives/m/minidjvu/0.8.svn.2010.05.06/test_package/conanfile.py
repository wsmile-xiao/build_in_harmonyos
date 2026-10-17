import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class MinidjvuTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if can_run(self):
            test_dir = os.path.join(self.cpp.build.bindir, "test_minidjvu")
            ohos_test = os.path.join(self.cpp.build.bindir, "test_minidjvu_ohos")
            self.run(test_dir, env="conanrun")
            self.run(ohos_test, env="conanrun")
            self.run("minidjvu --version", env="conanrun")
