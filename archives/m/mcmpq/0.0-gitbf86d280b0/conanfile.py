#!/usr/bin/env python3
"""Conan recipe — mcmpq 0.0-gitbf86d280b0 (header-only C11 MPMC queue).

Header-only library: no build system, no compiled artifacts.
Upstream ships mcmpq.h + readme.txt + tests/ (basic.c, fuzz.c, a.out);
test sources are not installed into the package; consumers include
mcmpq.h directly. HarmonyOS-specific test (ohos_specific_test.c) is
adapter-added under test_package/ and shipped as real test source.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class McmpqConan(ConanFile):
    name = "mcmpq"
    version = "0.0-gitbf86d280b0"
    description = "Ultra-high-performance, static, brutalist, single-header, multi-producer multi-consumer queue library in C11."
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/173duprot/mcmpq.h"
    url = "https://github.com/173duprot/mcmpq.h"

    package_type = "library"

    # 无编译产物 → settings 仅保留结构一致性；package_id 清空见下
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
        # header-only：无编译阶段；仅应用 conandata 补丁（当前 patches 为空）
        apply_conandata_patches(self)

    def package(self):
        # 变体 A: header-only 库 — 只安装 mcmpq.h
        copy(self, "mcmpq.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        # 标准头文件信息
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "mcmpq")
        self.cpp_info.set_property("cmake_target_name", "mcmpq::mcmpq")