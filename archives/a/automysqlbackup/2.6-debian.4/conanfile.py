#!/usr/bin/env python3
"""Conan recipe — automysqlbackup 2.6-debian.4 (MySQL backup script)

automysqlbackup 提供 automysqlbackup 命令（单文件 bash 脚本——MySQL
自动备份脚本——无编译——运行依赖 mysql/mysqldump/gzip 等外部命令）。
路径 A 基础适配。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AutomysqlbackupConan(ConanFile):
    name = "automysqlbackup"
    version = "2.6-debian.4"
    description = "automysqlbackup — automatic MySQL backup script"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/automysqlbackup/"
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
        # 无编译（单文件 bash 脚本——无需构建）

    def package(self):
        src_dir = self.source_folder
        # 手动安装 automysqlbackup 脚本（源码已含执行位——安装到 bin/）
        copy(self, "automysqlbackup", src=src_dir,
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
