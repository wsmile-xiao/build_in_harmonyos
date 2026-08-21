#!/usr/bin/env python3
"""Conan recipe — autotalent 0.2 (LADSPA pitch-correction plugin)

autotalent 是 LADSPA 音高修正插件（C 单文件 + 自带 mayer_fft FFT），
构建为 autotalent.so（make，无外部库依赖）。路径 A 基础适配。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AutotalentConan(ConanFile):
    name = "autotalent"
    version = "0.2"
    description = "autotalent — LADSPA plugin for real-time pitch correction"
    license = "GPL-2.0-or-later"
    homepage = "http://tombaran.info/autotalent.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder
        # make（in-source——autotalent.so LADSPA 插件；Makefile 相对路径）
        self.run(
            f"umask 000 && cd {src_dir} && "
            # Makefile 的 CC=gcc——OHOS 无 gcc（用 clang）→ 注入 CC
            f"make CC=/data/service/hnp/bin/clang -j1",
            env="conanbuild",
        )

    def package(self):
        src_dir = self.source_folder
        # 打包 autotalent.so（LADSPA 插件）+ LICENSE
        copy(self, "autotalent.so", src=src_dir,
             dst=os.path.join(self.package_folder, "ladspa"), keep_path=False)
        copy(self, "COPYING", src=src_dir,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
