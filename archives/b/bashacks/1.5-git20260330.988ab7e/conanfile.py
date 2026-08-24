#!/usr/bin/env python3
"""Conan recipe — bashacks 1.5-git20260330.988ab7e (bash 函数库)

bashacks 提供 bashacks.sh（bash 函数库——make 用 cat 合并 src/ 的
bh_*.sh 生成——无编译依赖——bash 增强函数库，source 后调用 bh_* 函数）。
路径 A 基础适配。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BashacksConan(ConanFile):
    name = "bashacks"
    version = "1.5-git20260330.988ab7e"
    description = "bashacks — bash 函数库（网络/加密/文件系统等增强函数）"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/caladan/bashacks"
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
        # make（cat 合并 src/ 的 bh_*.sh 生成 bashacks.sh——无编译）
        self.run(f"umask 000 && cd {src_dir} && make -j1",
                 env="conanbuild")

    def package(self):
        src_dir = self.source_folder
        # 手动安装（bashacks 无 install 目标——Makefile 仅 all/clean——
        # bashacks.sh 函数库安装到 share/bashacks/）
        copy(self, "bashacks.sh", src=src_dir,
             dst=os.path.join(self.package_folder, "share", "bashacks"),
             keep_path=False)
        copy(self, "LICENSE", src=src_dir,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
