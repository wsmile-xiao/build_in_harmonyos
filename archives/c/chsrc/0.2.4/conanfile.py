#!/usr/bin/env python3
"""Conan recipe — chsrc 0.2.4（全平台换源工具与框架）.

chsrc 是用 C11 编写的全平台换源工具，支持 Linux/Windows/macOS/BSD/Android 等系统。
构建系统：Makefile
平台：OHOS aarch64 / Linux / macOS / Windows
依赖：零运行时依赖（纯 C 语言，无外部库依赖）
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class ChsrcConan(ConanFile):
    name = "chsrc"
    version = "0.2.4"
    description = "chsrc — 全平台通用换源工具与框架，支持多种操作系统和软件的镜像源切换"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/RubyMetric/chsrc"
    url = ""

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # chsrc 零运行时依赖

    def generate(self):
        # AutotoolsToolchain 生成 conanbuild 环境，
        # 通过 env="conanbuild" 使 make 继承交叉编译器的 CC/CFLAGS 设置
        tc = AutotoolsToolchain(self)
        tc.make_args = []
        # 项目特有的 include 路径通过 tc.extra_cflags 追加，不覆盖工具链的编译标志
        tc.extra_cflags = ["-Iinclude", "-Ilib"]
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # chsrc 使用 Makefile 构建
        # CC 通过 shell 环境变量传入（非 make 命令行），允许 AutotoolsToolchain
        # 的交叉编译器 CC 通过 env="conanbuild" 环境覆盖（?= 语义）
        # CFLAGS 由 AutotoolsToolchain 的 extra_cflags + 工具链标志合并提供
        self.run("make build-in-release-mode", env="conanbuild")

    def package(self):
        self.run(f"make install PREFIX=/usr INSTALL_BIN=chsrc-release DESTDIR={self.package_folder}")

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["usr/bin"]
        self.cpp_info.libdirs = []
