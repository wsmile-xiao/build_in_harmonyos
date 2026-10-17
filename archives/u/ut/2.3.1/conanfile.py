#!/usr/bin/env python3
"""Conan recipe — boost-ext/ut 2.3.1 (header-only C++ testing framework).

- 无编译阶段（header-only）：package() 仅拷贝头文件与许可证。
- R34: test_package 真实 include/使用 boost/ut.hpp，非空壳。
- R51: 上游测试（test/ut + test/ft）已清点并如实申报于 MANIFEST.yml。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class UtConan(ConanFile):
    name = "ut"
    version = "2.3.1"
    description = "ut: C++20 single-header/single-module, macro-free Testing Framework"
    license = "MIT"
    homepage = "https://github.com/boost-ext/ut"
    url = "https://github.com/boost-ext/ut"

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
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.cppm", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []