#!/usr/bin/env python3
"""Conan recipe — backupninja 1.2.2 (backup automation framework)

backupninja 提供 backupninja 命令（shell 脚本工具——autotools 构建，
无编译依赖——src/ 主脚本 + handlers/ 备份处理脚本 + etc/ 配置）。
路径 A 基础适配。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BackupninjaConan(ConanFile):
    name = "backupninja"
    version = "1.2.2"
    description = "backupninja — lightweight, extensible backup system"
    license = "GPL-2.0-or-later"
    homepage = "https://0xacab.org/riseup/backupninja"
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
        # configure + make（shell 脚本安装——无编译；configure 常规运行）
        self.run(
            f"umask 000 && cd {src_dir} && ./configure",
            env="conanbuild",
        )
        self.run(
            f"umask 000 && cd {src_dir} && make -j1",
            env="conanbuild",
        )

    def package(self):
        src_dir = self.source_folder
        # DESTDIR install（backupninja 脚本 + handlers/ + etc/ 配置）
        self.run(
            f"umask 000 && cd {src_dir} && "
            f"make install DESTDIR={self.package_folder}",
            env="conanbuild",
        )
        # install 安装的脚本缺执行位（install-sh -m 权限）→ 补 chmod +x
        # （backupninja/ninjahelper——R34 实际运行需可执行）
        for exe in ("backupninja", "ninjahelper"):
            # backupninja 实际安装在 usr/local/sbin（configure 默认
            # prefix=/usr/local——sbindir=/usr/local/sbin）
            pth = os.path.join(self.package_folder, "usr", "local", "sbin", exe)
            if os.path.exists(pth):
                os.chmod(pth, 0o755)
        copy(self, "COPYING", src=src_dir,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["usr/sbin"]
