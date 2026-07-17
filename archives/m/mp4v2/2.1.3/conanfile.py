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

    def generate(self):
        tc = CMakeToolchain(self)
        # 关键：告诉CMake忽略最低版本要求，直接使用3.5的策略
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
