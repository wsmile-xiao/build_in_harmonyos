#!/usr/bin/env python3
"""Conan recipe — pocketfft release_for_eigen (header-only C++ FFT library).

PocketFFT 是纯头文件 C++11 库（pocketfft_hdronly.h），上游 tar 包无构建系统，
无编译阶段；package 阶段仅复制头文件与 LICENSE（headeronly 变体 A，v12.21）。
R34: test_package 必须真实调用被测库 API（test.c 实际 include 并使用接口）。
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

import os


class PocketfftConan(ConanFile):
    name = "pocketfft"
    version = "release_for_eigen"
    description = "PocketFFT - heavily modified implementation of FFTPack for C++ (header-only)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/mreineck/pocketfft"
    url = ""  # CI fills this

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
        # 无编译阶段：header-only 库无编译产物，无 configure/make。
        # 当前 conandata 无补丁（patches: {}），此处仅保持补丁管线完整性（R34 不伪造编译日志）。
        apply_conandata_patches(self)

    def package(self):
        # 变体 A: header-only 库（显式 package_folder 绝对路径，Conan Center 标准写法）
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.hpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        # 变体 A: 标准头文件信息
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
