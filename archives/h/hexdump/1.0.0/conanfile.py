#!/usr/bin/env python3
"""Conan recipe — hexdump 1.0.0 (header-only C++14 hexdump library).

Upstream: https://github.com/FernandoVelcic/hexdump (tag 1.0.0)
Header-only library: 唯一公开头文件 hexdump.hpp，安装到 include/。
无编译阶段（build() 仅应用补丁，当前 patches: {} 为空，不产生编译日志——R34），
test_package 通过真实调用 Hexdump/CustomHexdump API 做消费者验证。
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

import os


class HexdumpConan(ConanFile):
    name = "hexdump"
    version = "1.0.0"
    description = "A header-only hexdump library for C++14 streams (FernandoVelcic/hexdump)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/FernandoVelcic/hexdump"
    url = ""  # CI fills this
    topics = ("hexdump", "cpp", "header-only", "streams")

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
        # Header-only：无编译阶段，仅应用 conandata.yml 登记的补丁
        # （R34：不产生伪造编译日志）。
        apply_conandata_patches(self)

    def package(self):
        copy(self, "hexdump.hpp",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # header-only：单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "hexdump")
        self.cpp_info.set_property("cmake_target_name", "hexdump::hexdump")
