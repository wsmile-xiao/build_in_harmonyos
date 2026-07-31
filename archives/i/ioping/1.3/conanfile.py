#!/usr/bin/env python3
"""Conan recipe — ioping 1.3（磁盘 I/O 延迟测量工具）.

ioping 是一个轻量级磁盘 I/O 延迟测量工具，类似 ping 测量网络延迟的方式。
构建系统：Makefile
平台：OHOS aarch64 / Linux / macOS
依赖：零运行时依赖（仅需系统 libm、librt）
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class IopingConan(ConanFile):
    name = "ioping"
    version = "1.3"
    description = "ioping — simple disk I/O latency measuring tool"
    license = "GPL-3.0-only"
    homepage = "https://github.com/koct9i/ioping"
    url = ""

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # ioping 零运行时依赖

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # ioping 使用 Makefile 构建。补丁已将 CC = 改为 CC ?=，环境变量
        # 中的交叉编译器（由 Conan profile 设置）会自动生效，无需命令行传入。
        self.run("make all")

        # 上游 make test：只在 native 编译时运行，交叉编译时跳过
        if not cross_building(self):
            self.run("make test")

    def package(self):
        self.run(f"make install PREFIX=/usr DESTDIR={self.package_folder}")

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["usr/bin"]
        self.cpp_info.libdirs = []
