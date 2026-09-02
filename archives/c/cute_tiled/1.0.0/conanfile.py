#!/usr/bin/env python3
"""Conan recipe — cute_tiled 1.0.0 (single-header C library, bootstrap skeleton).

cute_tiled 是 RandyGaul/cute_headers 系列的单头文件 C 库，用于加载 Tiled JSON
地图。1.0.0 阶段对应上游 tinytiled.h v1.00（引入 commit 17014665d51e）。
header-only：使用方在自己的翻译单元 #define CUTE_TILED_IMPLEMENTATION 后包含。

当前为 bootstrap 骨架，尚未编译验证；后续 adapt 阶段完善。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CuteTiledConan(ConanFile):
    name = "cute_tiled"
    version = "1.0.0"
    description = "Very efficient loader for Tiled maps exported to JSON format"
    license = "zlib"
    homepage = "https://github.com/RandyGaul/cute_headers"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # header-only 库：所有 settings 组合产出相同的包内容
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # header-only 库无编译步骤；补丁在 source() 阶段已应用
        pass

    def package(self):
        # 上游 1.0.0 阶段头文件名为 tinytiled.h，按 cute_tiled 名称装入 include/
        src_hdr = os.path.join(self.source_folder, "tinytiled.h")
        if not os.path.exists(src_hdr):
            src_hdr = os.path.join(self.source_folder, "cute_tiled.h")
        copy(self, os.path.basename(src_hdr), os.path.dirname(src_hdr),
             os.path.join(self.package_folder, "include"),
             keep_path=False)
        # 统一暴露为 cute_tiled.h（供使用方稳定包含）
        os.replace(
            os.path.join(self.package_folder, "include", os.path.basename(src_hdr)),
            os.path.join(self.package_folder, "include", "cute_tiled.h"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.defines = []
