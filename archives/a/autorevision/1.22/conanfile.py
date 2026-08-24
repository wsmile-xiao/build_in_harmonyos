#!/usr/bin/env python3
"""Conan recipe — autorevision 1.22 (VCS revision metadata generation)

autorevision 提供 autorevision 命令（shell/awk 脚本——Makefile 构建，
sed 从 autorevision.sh 生成——无编译依赖——从 VCS 元数据生成版本信息）。
路径 A 基础适配。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AutorevisionConan(ConanFile):
    name = "autorevision"
    version = "1.22"
    description = "autorevision — extract revision metadata from VCS repositories"
    license = "ISC"
    homepage = "https://github.com/Autorevision/autorevision"
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
        # make autorevision（只生成 autorevision 命令——sed 替换版本；
        # 不构建 autorevision.1 man 页——需 asciidoc/a2x（OHOS 沙箱无，
        # Error 127 command not found））
        self.run(f"umask 000 && cd {src_dir} && make autorevision -j1",
                 env="conanbuild")

    def package(self):
        src_dir = self.source_folder
        # 手动安装 autorevision 命令（make install 依赖 man 页——跳过）
        copy(self, "autorevision",
             src=os.path.join(src_dir),
             dst=os.path.join(self.package_folder, "usr", "local", "bin"),
             keep_path=False)
        copy(self, "COPYING.md", src=src_dir,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["usr/local/bin"]
