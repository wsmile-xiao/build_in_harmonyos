#!/usr/bin/env python3
"""Conan recipe — HandmadeMath 2.0.0 (header-only C/C++ math library).

变体 A (header-only): 无编译，仅拷贝 HandmadeMath.h 到头文件目录。
R34: test_package 必须真实 include 并使用 HandmadeMath API，不能空壳。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class HandmadeMathConan(ConanFile):
    name = "handmade-math"
    version = "2.0.0"
    description = "HandmadeMath - a simple C/C++ header-only math library for games and graphics"
    license = "CC0-1.0"
    homepage = "https://github.com/HandmadeMath/HandmadeMath"
    url = "https://github.com/HandmadeMath/HandmadeMath"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only: 无编译产物，仅应用补丁（不得伪造编译日志——R34）
        apply_conandata_patches(self)


    def package(self):
        copy(self, "HandmadeMath.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler -> 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
