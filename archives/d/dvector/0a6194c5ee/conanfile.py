#!/usr/bin/env python3
"""Conan recipe — dvector 0a6194c5ee (Header-only C/C++ math library).

dvector 是单文件 2D/3D 向量/四元数/矩阵数学库（原基于 ccVector），
采用 CC0 公共领域许可。无构建系统，属 header-only 无构建族（v12.21 模板）。
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout

import os


class DvectorConan(ConanFile):
    name = "dvector"
    version = "0a6194c5ee"
    description = "Portable single-file 2D/3D vector/quaternion/matrix math library"
    license = "CC0-1.0"
    homepage = "https://github.com/BareRose/dvector"
    url = ""  # CI fills this

    package_type = "header-library"

    # 无编译产物 → settings 仅保留结构一致性；package_id 清空见下
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # header-only 无编译阶段：build() 留空（R34：不得伪造编译日志）
    def build(self):
        pass

    def package(self):
        # ── 变体 A: header-only 库 ──
        # 注意：conan 2 的 copy() 相对 dst 以 package_folder 为基准，
        # 显式拼接 self.package_folder 保证头文件落入包内 include/。
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
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "dvector")
        self.cpp_info.set_property("cmake_target_name", "dvector::dvector")
