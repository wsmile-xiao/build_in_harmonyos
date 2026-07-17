import os
from conan import ConanFile
from conan.tools.files import get, copy
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
        # 修复 CMake 版本
        cmake_file = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cmake_file, "r") as f:
            content = f.read()
        content = content.replace("cmake_minimum_required(VERSION 2.8)", "cmake_minimum_required(VERSION 3.15)")
        with open(cmake_file, "w") as f:
            f.write(content)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # 手动复制库文件
        copy(self, "*.so*", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # 复制头文件
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"), dst=os.path.join(self.package_folder, "include"), keep_path=True)

    def package_info(self):
        self.cpp_info.libs = ["mp4v2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
