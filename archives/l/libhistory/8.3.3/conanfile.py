#!/usr/bin/env python3
"""Conan recipe — libhistory 8.3.3 (GNU History library from readline 8.3, Autotools)

版本语义：libhistory 与 GNU readline 同源同版发布，无独立上游 tarball。
8.3.3 = readline-8.3 基线 + 官方补丁 readline83-001/002/003，沿用官方
readline-8.2.13 的「基线.补丁数」命名惯例。本包仅交付 history 组件。
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class LibhistoryConan(ConanFile):
    name = "libhistory"
    version = "8.3.3"
    description = "GNU History library — command line history management (from GNU readline)"
    license = "GPL-3.0-only"
    homepage = "https://tiswww.cwru.edu/php/chet/readline/rltop.html"
    topics = ("history", "cli", "command-line")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    # history 库不使用 termcap/ncurses，无依赖

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: readline 系统同名库族 — 静态编译，避免 .so 污染 /lib /lib64
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        # history 库不需要 termcap，不传 --with-curses（仅影响 readline 行编辑部分）
        # 静态库需 -fPIC 才能链入下游共享库（OHOS musl 默认 BIND_NOW）
        tc.extra_cflags.append("-fPIC")
        tc.extra_cflags.append("-O2")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: umask 077 阻止 config.status 在 mktemp 目录内写入（同 readline 8.3 配方）
        self.run(f"sed -i 's/umask 077/umask 002/g' {self.source_folder}/configure")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 仅交付 history 组件：lib 移除 readline 项；
        # include/readline 头文件全集保留（history.h 依赖 rltypedefs.h/rlstdc.h 等）
        rm(self, "libreadline*", os.path.join(self.package_folder, "lib"))
        rm(self, "readline.pc", os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["history"]
