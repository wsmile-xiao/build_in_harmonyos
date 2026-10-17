#!/usr/bin/env python3
"""Conan recipe — lib_fts 1.2.8 (Header-only, 无构建打包族 变体 A).

上游 forrestthewoods/lib_fts 是 STB 风格单文件库集合；C++ 交付物为
code/fts_fuzzy_match.h（header-only，ns fts，公开 API：fuzzy_match /
fuzzy_match_simple）。上游无构建系统、无 git tag（master 快照，头文件自声明
v0.2.0）；任务版本 1.2.8 为任务侧口径。本配方打包头文件到 include/，
不编译（R34：test_package 真实调用公开 API，见 test_package/）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class LibftsConan(ConanFile):
    name = "lib_fts"
    version = "1.2.8"
    description = "Single-file public domain libraries (fts_fuzzy_match fuzzy text search)"
    license = "Unlicense"
    homepage = "https://github.com/forrestthewoods/lib_fts"
    url = "https://github.com/forrestthewoods/lib_fts"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    def export_sources(self):
        pass  # patches/* 已由 exports_sources 导出；无额外源文件

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)  # conandata.yml patches 段（当前为空，无操作）

    # Header-only：无编译阶段，build() 显式留空（R34：不得伪造编译日志）
    def build(self):
        pass

    def package(self):
        # ── 变体 A: header-only 库 —— 头文件位于 code/ 与 code/util/ 子目录
        pkg_include = os.path.join(self.package_folder, "include")
        print(f"DEBUG pkg_include={pkg_include}")
        copy(self, "fts_fuzzy_match.h",
             src=os.path.join(self.source_folder, "code"),
             dst=pkg_include, keep_path=False)
        copy(self, "fts_hashutil.h",
             src=os.path.join(self.source_folder, "code", "util"),
             dst=pkg_include, keep_path=False)
        copy(self, "fts_timer.h",
             src=os.path.join(self.source_folder, "code", "util"),
             dst=pkg_include, keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []