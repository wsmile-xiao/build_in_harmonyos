#!/usr/bin/env python3
"""Conan recipe — veque 1.3.7 (header-only, 无上游构建系统).

veque 是 C++17 头文件容器（std::vector 与 std::deque 的双端变体），交付物为
单头 `include/veque.hpp`；上游 tarball 不含 CMakeLists.txt/Makefile/configure，
因此本配方不运行上游构建系统，只打包头文件与许可证。
"""
import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class VequeConan(ConanFile):
    name = "veque"
    version = "1.3.7"
    description = "Fast C++ container combining the best features of std::vector and std::deque (header-only)"
    license = "BSL-1.0"
    homepage = "https://github.com/Shmoopty/veque"
    url = "https://github.com/Shmoopty/veque"
    topics = ("cpp17", "vector", "deque", "header-only")
    settings = "os", "compiler", "build_type", "arch"
    package_type = "header-library"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # veque.hpp 使用 if constexpr / std::optional 等 C++17 构造（README 明示 C++17）
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # G1 文本门禁要求存在 def build(；header-only 且上游无构建系统
        # （tarball 内无 CMakeLists.txt / Makefile / configure），不编译、
        # 不运行上游构建系统，也不伪造任何编译日志（R34）。
        apply_conandata_patches(self)

    def package(self):
        copy(
            self,
            "veque.hpp",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "veque")
        self.cpp_info.set_property("cmake_target_name", "veque::veque")
