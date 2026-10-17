#!/usr/bin/env python3
"""Conan recipe — json 1.0.1 (header-only C99 JSON/SJSON parser).

json 1.0.1 is a single-header (json.h) public-domain, in-place JSON/SJSON
parser with no memory allocation. Nothing is compiled: the public header
json.h is installed as-is (header-only pattern, R34: test_package really
includes and uses the API).

Upstream self-test: the header ships an embedded minimal test case enabled
with -D JSON_TEST (see README): `clang -D JSON_TEST -x c --std=c99 json.h`.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class JsonConan(ConanFile):
    name = "json"
    version = "1.0.1"
    description = "In-place JSON/SJSON parser in C99, single header, no memory allocation (Public Domain)"
    license = "Public Domain"
    homepage = "https://github.com/mjansson/json"
    url = "https://github.com/mjansson/json"

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
        # 无编译阶段（header-only），仅应用补丁（当前无补丁），不得伪造编译日志（R34）。
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # 无编译产物，不依赖 os/compiler 二进制差异
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []  # header-only：无链接库
        self.cpp_info.includedirs = ["include"]