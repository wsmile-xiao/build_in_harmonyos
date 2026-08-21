#!/usr/bin/env python3
"""Conan recipe — brightnessctl 0.5.1 (brightness control CLI tool)

brightnessctl 提供 brightnessctl 命令（C 单文件，Makefile 构建——
sysfs 背光控制，无外部库依赖（LDLIBS=-lm），libsystemd 可选）。
路径 A 基础适配。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BrightnessctlConan(ConanFile):
    name = "brightnessctl"
    version = "0.5.1"
    description = "brightnessctl — read and control device brightness"
    license = "MIT"
    homepage = "https://github.com/Hummer12007/brightnessctl"
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
        # make（in-source——brightnessctl 可执行；Makefile 相对路径 +
        # 默认 CC 是 gcc——OHOS 无 gcc → 注入 CC=clang，同 autotalent 先例）
        self.run(
            f"umask 000 && cd {src_dir} && "
            # 补丁 0001 改 Makefile（CFLAGS 加 -D__linux__——OHOS 编译时
            # __linux__ 未定义触发 "only supports Linux" 检查；VERSION 0.5.1）
            f"make CC=/data/service/hnp/bin/clang -j1",
            env="conanbuild",
        )

    def package(self):
        src_dir = self.source_folder
        # DESTDIR install（brightnessctl 到 bin/；Makefile 的 DESTDIR 支持）
        self.run(
            f"umask 000 && cd {src_dir} && "
            f"make install DESTDIR={self.package_folder} PREFIX=/usr "
            f"INSTALL_UDEV_RULES=0",
            env="conanbuild",
        )
        copy(self, "LICENSE", src=src_dir,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["usr/bin"]
