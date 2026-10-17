#!/usr/bin/env python3
"""Conan recipe — ghc-filesystem 1.5.14 (header-only, CMake INTERFACE).

ghc::filesystem 是 C++17 std::filesystem 的可移植 header-only 实现。
上游以 INTERFACE target ghc_filesystem 交付 include/ 头文件，无编译产物。
OHOS PC 上直接打包 include/ghc/*.hpp 即可，无需任何编译与系统依赖。
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class GhcFilesystemConan(ConanFile):
    name = "ghc-filesystem"
    version = "1.5.14"
    description = "A header-only C++17 std::filesystem compatible implementation (ghc::filesystem)."
    license = "MIT"
    homepage = "https://github.com/gulrak/filesystem"
    url = "https://github.com/gulrak/filesystem"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 应用 conandata.yml 声明的补丁（本库 patches 为空，无实际应用；G1 配方完整性要求此调用）
        apply_conandata_patches(self)

    def package(self):
        # header-only：分发 include/ghc/ 全部头文件（filesystem.hpp / fs_*.hpp / fs_std*.hpp）
        # 注意：copy() 的 src 为 include/，模式需相对该目录用 ghc/*（不能用 include/ghc/*）
        copy(self, "ghc/*", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        # 与上游 CMake target alias 对齐：ghcFilesystem::ghc_filesystem
        self.cpp_info.set_property("cmake_file_name", "ghc-filesystem")
        self.cpp_info.set_property("cmake_target_name", "ghc_filesystem")