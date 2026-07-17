import os
from conan import ConanFile
from conan.tools.files import get
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout

class Mp4v2Conan(ConanFile):
    name = "mp4v2"
    version = "2.1.3"
    description = "A C++ library for reading and writing MP4 files"
    homepage = "https://mp4v2.org/"
    license = "MPL-1.1"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # 直接重写 CMakeLists.txt 第一行
        cmake_file = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cmake_file, "r") as f:
            lines = f.readlines()
        lines[0] = "cmake_minimum_required(VERSION 3.15)\n"
        with open(cmake_file, "w") as f:
            f.writelines(lines)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["mp4v2"]
