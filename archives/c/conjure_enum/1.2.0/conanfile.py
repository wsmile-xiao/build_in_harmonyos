#!/usr/bin/env python3
"""Conan recipe — conjure_enum 1.2.0 (CMake header-only C++20 library).

conjure_enum 是轻量 header-only C++20 enum/typename 反射库（INTERFACE library，
仅安装 include/fix8/*.hpp），无二进制编译。配方采用 header-only 打包族：
source 阶段打补丁后直接 copy 头文件，无 build()，package_id 清空。

OHOS 适配（libcxx-ohos clang 15 工具链缺口，见 patches/）：
  - libcxx-ohos 无 <source_location>：__has_include 能力探测 + tpeek()/epeek()
    缺失时回退 __PRETTY_FUNCTION__（与 clang 原生 function_name 同形态）
  - libcxx-ohos <format> 头存在但 __cpp_lib_format 符号缺失：to_hex_string 守卫
    改为 defined(__cpp_lib_format) && __has_include(<format>)，回退 ostringstream
  - clang15 对 requires-clause 内 decltype(T::ce_first) 硬报错：改 requires requires
"""
from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
import os


class ConjureEnumConan(ConanFile):
    name = "conjure_enum"
    version = "1.2.0"
    description = "Lightweight C++20 enum and typename reflection"
    license = "MIT"
    homepage = "https://github.com/fix8mt/conjure_enum"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def package_id(self):
        # header-only 库：所有 settings 组合产出相同包内容
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # header-only：无编译阶段，build() 留空（不得伪造编译日志 — R34）
    def build(self):
        pass

    def package(self):
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "LICENSE*", src=self.source_folder,
             dst="licenses", keep_path=False)

    def package_info(self):
        # 变体 A: 标准头文件信息（无 bin/lib 目录）
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.requires = []
