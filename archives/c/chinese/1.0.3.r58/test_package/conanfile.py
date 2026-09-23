from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os
import shlex


class ChineseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        test_executable = os.path.join(self.cpp.build.bindir, "chinese_consumer_test")
        self.run(f"{shlex.quote(test_executable)} {shlex.quote(package)}", env="conanrun")
