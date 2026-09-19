#!/usr/bin/env python3
"""Conan recipe — wide-integer 1.01（header-only C++20 任意精度整数库）.

Upstream: https://github.com/ckormanyos/wide-integer
Header-only library: 唯一公开头文件 math/wide_integer/uintwide_t.h，
安装到 include/math/wide_integer/（与上游 CMake install 保持一致）。
无编译阶段（build() 仅应用补丁，当前 patches: {} 为空，不产生编译日志——R34），
test_package 通过真实调用 uintwide_t API 做消费者验证。
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

import os


class WideIntegerConan(ConanFile):
    name = "wide-integer"
    version = "1.01"
    description = "Wide-Integer: header-only C++20 arbitrary-precision integer arithmetic library"
    license = "BSL-1.0"
    homepage = "https://github.com/ckormanyos/wide-integer"
    url = ""  # CI fills this
    topics = ("bigint", "arbitrary-precision", "header-only", "cpp20", "math")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only：无编译阶段，仅应用 conandata.yml 登记的补丁 0001
        # （R34：不产生编译日志）。
        apply_conandata_patches(self)

    def package(self):
        copy(self, "uintwide_t.h",
             src=os.path.join(self.source_folder, "math", "wide_integer"),
             dst=os.path.join(self.package_folder, "include", "math", "wide_integer"))
        copy(self, "LICENSE_1_0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # header-only：单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "wide-integer")
        self.cpp_info.set_property("cmake_target_name", "wide-integer::wide-integer")
        self.cpp_info.set_property("cmake_find_mode", "both")
