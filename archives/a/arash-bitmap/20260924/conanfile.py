#!/usr/bin/env python3
"""Conan recipe — arash-bitmap 20260924 (header-only C++ library).

The C++ Bitmap Library (Arash Partow) is a single-header implementation
(bitmap_image.hpp): no build step, no external dependencies.
Variante A of the header-only template: package the public header into
include/ and let consumers compile against it directly.

上游测试: bitmap_test.cpp 提供 20 个独立 test 函数 (test01..test20),
单独编译运行 (见 test_package/)。R34: test_package 实际 include 并使用
公共接口 (bitmap_image / image_drawer), 非空壳打印。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class ArashbitmapConan(ConanFile):
    name = "arash-bitmap"
    version = "20260924"
    description = "The C++ Bitmap Library - 24-bit per pixel bitmap image reader/writer (single header)"
    license = "MIT"
    homepage = "http://partow.net/programming/bitmap/index.html"
    url = "https://github.com/ArashPartow/bitmap"

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
        # header-only: 无编译步骤；仅应用配方补丁（当前 patches 为空）
        apply_conandata_patches(self)

    def package(self):
        include_dir = os.path.join(self.package_folder, "include")
        os.makedirs(include_dir, exist_ok=True)
        src = self.source_folder
        # 显式复制头文件（与仓库既有 header-only/数据配方一致，避免 copy() 通配歧义）
        shutil.copy2(os.path.join(src, "bitmap_image.hpp"),
                     os.path.join(include_dir, "bitmap_image.hpp"))
        # 无 LICENSE 文件时跳过
        lic = os.path.join(src, "LICENSE")
        if os.path.exists(lic):
            lic_dir = os.path.join(self.package_folder, "licenses")
            os.makedirs(lic_dir, exist_ok=True)
            shutil.copy2(lic, os.path.join(lic_dir, "LICENSE"))

    def package_id(self):
        self.info.clear()          # 无构建依赖 → 单一 package_id

    def package_info(self):
        # 变体 A: 标准头文件信息
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "arash-bitmap")
        self.cpp_info.set_property("cmake_target_name", "arash-bitmap::arash-bitmap")
