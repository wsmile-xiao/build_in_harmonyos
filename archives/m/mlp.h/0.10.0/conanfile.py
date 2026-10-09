#!/usr/bin/env python3
"""Conan recipe — mlp.h 0.10.0 (header-only C library)

A tiny, dependency-free single-header Multi-Layer Perceptron library for C.
No build system, no linking: consumers only need the MLP.h header.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class MlpHConan(ConanFile):
    name = "mlp.h"
    version = "0.10.0"
    description = "A tiny, dependency-free single-header Multi-Layer Perceptron library for C"
    license = "MIT"
    homepage = "https://github.com/px7nn/MLP.h"
    url = ""  # CI fills this

    package_type = "header-library"

    # 无编译产物 -> settings 仅保留结构一致性；package_id 清空见 package_id()
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    # 不定义 layout()：dst 一律用绝对 package_folder 路径，避免相对路径
    # 解析到 build 目录（header-only 无构建步骤）

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：仅应用 conandata 声明补丁，无编译步骤
        apply_conandata_patches(self)

    def package(self):
        copy(self, "MLP.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler -> 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
