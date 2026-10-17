#!/usr/bin/env python3
"""Conan recipe — etl 20.38.4 (Embedded Template Library, header-only C++)."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class EtlConan(ConanFile):
    name = "etl"
    version = "20.38.4"
    description = "The Embedded Template Library (header-only C++ template library for embedded applications)"
    license = "MIT"
    homepage = "https://www.etlcpp.com"
    url = "https://github.com/ETLCPP/etl"
    topics = ("embedded", "template", "stl", "header-only", "c++", "cpp")

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：无编译步骤；保留补丁管线（当前 patches: [] 为空操作）
        apply_conandata_patches(self)

    def package(self):
        # include/etl/ 全部头文件
        copy(self, "*",
             os.path.join(self.source_folder, "include", "etl"),
             os.path.join(self.package_folder, "include", "etl"))
        copy(self, "LICENSE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
