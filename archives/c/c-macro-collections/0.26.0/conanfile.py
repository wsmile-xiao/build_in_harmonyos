#!/usr/bin/env python3
"""Conan recipe — c-macro-collections 0.26.0 (header-only macro C11 collections).

C Macro Collections 是纯宏驱动的 C11 通用数据结构库（header-only）：
src/cmc/ 下 16 个主头文件（list/hashmap/stack/treemap/...）+ cmc/cmc/<name>/
实现子目录 + cmc/utl/ 工具头 + cmc/cor/ 核心头，无任何 .c 编译单元、无
configure/CMake install 目标（顶层 Makefile 仅驱动 tests/benchmarks）。
配方仅安装头文件树，无库目标（R26/R38：纯库，无 bin）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class CMacroCollectionsConan(ConanFile):
    name = "c-macro-collections"
    version = "0.26.0"
    description = "Easy to use, modular, header only, macro based, generic and type-safe Data Structures in C"
    license = "MIT"
    homepage = "https://github.com/LeoVen/C-Macro-Collections"
    url = "https://github.com/LeoVen/C-Macro-Collections"
    topics = ("c", "macro", "collections", "header-only", "generic", "data-structures")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # header-only 宏库，零运行时依赖
        pass

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only：所有 settings 组合产出相同包内容
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 无编译单元（纯宏头文件），无构建系统可调用
        apply_conandata_patches(self)

    def package(self):
        # 上游无 install 目标，直接从源码树收纳 src/cmc/ 头文件树到 include/
        # 消费者用法：`#define ... #include "cmc/list.h"`，包含根为 include/
        copy(self, "cmc/**", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "c-macro-collections")
        self.cpp_info.set_property("cmake_target_name", "c-macro-collections::c-macro-collections")
        self.cpp_info.libs = []
