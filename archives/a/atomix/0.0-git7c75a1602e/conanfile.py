#!/usr/bin/env python3
"""Conan recipe — atomix 0.0-git7c75a1602e (header-only, variant A).

atomix is a single-file, wait-free atomic sound mixing library.
It ships a single public header `atomix.h` (CC0/public domain) plus
optional test-only amalgamations under `libs/` (miniaudio.h, stb_vorbis.h)
used exclusively by the upstream `test.c` example — the library itself
has no build system and produces no compiled artifacts.

Header-only variant A per v12.21 template: no build() stage, package()
copies headers, clear package_id.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AtomixConan(ConanFile):
    name = "atomix"
    version = "0.0-git7c75a1602e"
    description = "Portable, single-file, wait-free atomic sound mixing library (header-only)"
    license = "CC0-1.0"
    homepage = "https://github.com/BareRose/atomix"
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

    # 无编译阶段：build() 为空（header-only，无编译日志可伪造——R34）；
    # 仅保留补丁应用钩子，当前 patches 为空
    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # 变体 A: header-only 库（dst 必须为 package_folder 下绝对路径，
        # 相对路径会在 build 目录落盘导致 consumers 找不到 include）
        copy(self, "atomix.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        # 变体 A: 标准头文件信息
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # 消费者需自行 define ATOMIX_IMPLEMENTATION（单 TU）或 ATOMIX_STATIC
