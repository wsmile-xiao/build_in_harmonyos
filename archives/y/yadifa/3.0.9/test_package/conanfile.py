import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class YadifaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test_yadifa_consumer.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_dir = os.path.join(self.dependencies["yadifa"].package_folder, "bin")
        exe = os.path.join(self.cpp.build.bindirs[0], "test_yadifa_consumer")
        self.run(f'"{exe}" "{bin_dir}"', env="conanrun")
