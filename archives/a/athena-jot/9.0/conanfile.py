#!/usr/bin/env python3
"""Conan recipe — athena-jot 9 (text/sequence generation tool)

athena-jot 提供 jot 命令（C 单文件，autotools 构建——BSD 风格的文本/
数字序列生成工具，仅标准头依赖）。路径 A 基础适配。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AthenajotConan(ConanFile):
    name = "athena-jot"
    version = "9.0"
    description = "athena-jot — print sequential or random data (BSD jot)"
    license = "BSD-3-Clause"
    homepage = "https://packages.debian.org/source/sid/athena-jot"
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
        # configure + make（tarball 含 configure——jot 单产物；CC 注入
        # clang——OHOS 无 gcc）
        self.run(
            f"umask 000 && cd {src_dir} && "
            f"./configure CC=/data/service/hnp/bin/clang",
            env="conanbuild",
        )
        self.run(
            f"umask 000 && cd {src_dir} && make -j1",
            env="conanbuild",
        )

    def package(self):
        src_dir = self.source_folder
        # DESTDIR install（jot 到 bin/ + jot.1 man 页）
        self.run(
            f"umask 000 && cd {src_dir} && "
            f"make install DESTDIR={self.package_folder}",
            env="conanbuild",
        )
        copy(self, "COPYING", src=src_dir,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["usr/local/bin"]
