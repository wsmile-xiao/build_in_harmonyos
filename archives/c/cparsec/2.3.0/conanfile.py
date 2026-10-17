#!/usr/bin/env python3
"""Conan recipe — cparsec 2.3.0 (header-only C parser combinator library).

CParseC 是单头文件 C99 解析器组合子库：上游无 configure/make 产物，仅分发
cparsec.h 一个头文件（无 libc 默认依赖，freestanding 友好）。因此本配方为
header-library 类型：source() 下载官方 tarball 后仅安装头文件，不编译。
上游测试（make test）在配方外部以 OHOS clang 编译运行，作为适配证据。

补丁说明（patches/0001-hoist-parser-defs-clang.patch）：
上游测试在函数体内用解析器宏定义局部解析器，依赖 GCC 嵌套函数扩展；
OHOS 工具链为 clang 15，不支持嵌套函数定义，故将解析器定义提升到文件
作用域（名称唯一、行为不变），测试断言逻辑保持不变。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout
import os


class CparsecConan(ConanFile):
    name = "cparsec"
    version = "2.3.0"
    description = "CParseC - C Parser Combinators (single-header C99 parser library)"
    license = "MIT"
    homepage = "https://github.com/PostgREST/CParseC"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 单头文件库，无强制第三方依赖（不假定 libc）
        pass

    def layout(self):
        basic_layout(self)

    def package_id(self):
        # header-only 库，所有 settings 组合产出相同的包内容
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # header-only：无需编译；上游测试的 OHOS clang 编译运行见 reports/
        pass

    def package(self):
        copy(self, "cparsec.h",
             src=os.path.join(self.source_folder),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        # header-only：无库文件，头文件在 include/
        self.cpp_info.set_property("cmake_file_name", "cparsec")
        self.cpp_info.set_property("cmake_target_name", "cparsec::cparsec")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []