#!/usr/bin/env python3
"""Conan recipe — verstable 2.2.1 (Header-only C/C++ library).

verstable is a single-header hash-table library (verstable.h). It has no
build system: consumers include the header directly. This recipe packages
the header into the include/ dir (R34: test_package actually instantiates
and uses the public API).

铁律对齐: R32 (settings.os 判断), R34 (test_package 真实调用 API),
R38 (纯库无 CLI → 不创建 commands.json).
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class VerstableConan(ConanFile):
    name = "verstable"
    version = "2.2.1"
    description = "Verstable — single-header hash-table library (C11 generic API and C++ template API)"
    license = "MIT"
    homepage = "https://github.com/JacksonAllan/Verstable"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only library: no compilation step exists upstream.
        # build() intentionally empty — nothing to compile (R34: 不伪造编译日志).
        apply_conandata_patches(self)

    def package(self):
        # 显式绝对路径: 避免 copy() 相对 dst 的基准歧义导致 include 未落入包内
        copy(self, "verstable.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建产物 → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "verstable")
        self.cpp_info.set_property("cmake_target_name", "verstable::verstable")
