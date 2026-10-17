#!/usr/bin/env python3
"""Conan recipe — cbehave 1.0.0 (Autotools).

cbehave: A Behavior Driven Development Framework for C.
Upstream repo: https://github.com/bigwhite/cbehave
License: Apache-2.0
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain


class CbehaveConan(ConanFile):
    name = "cbehave"
    version = "1.0.0"
    description = "cbehave - A Behavior Driven Development Framework for C"
    license = "Apache-2.0"
    homepage = "https://github.com/bigwhite/cbehave"
    url = "https://github.com/bigwhite/cbehave"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # cbehave 为纯 C 静态库，无第三方依赖
        pass

    def layout(self):
        # cbehave 为老式 autotools 项目（automake 1.11 生成 Makefile.in），
        # Makefile 使用相对 include 路径（-I../../src），与 conan 默认
        # out-of-source 布局（build-release/ 子目录）不兼容。
        # 改为 in-source 构建（build 目录 == source 目录）。
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # GitHub codeload zip 不保留可执行位: configure 及 GNU 辅助脚本
        # （config.guess/config.sub/depcomp/install-sh/missing）需补回 +x，
        # 否则 configure 报 "can't execute: Permission denied"。
        for f in ("configure", "config.guess", "config.sub",
                  "depcomp", "install-sh", "missing",
                  "src/example/configure", "src/example/config.guess",
                  "src/example/config.sub"):
            p = os.path.join(self.source_folder, f)
            if os.path.exists(p) and not os.access(p, os.X_OK):
                os.chmod(p, 0o755)
        autotools = Autotools(self)
        autotools.configure()
        # zip 解压后所有文件 mtime 相同，make 会误触发 autotools 重新生成
        # （系统无 aclocal-1.11）。touch 生成文件使 make 认为它们已是最新。
        for f in ("aclocal.m4", "configure", "Makefile.in",
                  "src/Makefile.in", "src/config.h.in", "src/example/Makefile.in"):
            p = os.path.join(self.source_folder, f)
            if os.path.exists(p):
                os.utime(p, None)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["cbehave"]
