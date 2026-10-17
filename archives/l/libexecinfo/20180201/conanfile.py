#!/usr/bin/env python3
"""Conan recipe — libexecinfo 20180201.

libexecinfo 提供 POSIX/GNU `execinfo.h` 回退实现（backtrace() /
backtrace_symbols() / backtrace_symbols_fd()），适用于无 glibc 内置
backtrace 的平台（OHOS/musl 系）。上游为纯 Makefile 构建，无 configure。

配方要点：
- build(): 在源码目录直接 make（Makefile 不支持 out-of-source），-j1。
- package(): 不依赖上游 `make install`（其 ln -s 硬编码 /usr/lib 绝对路径，
  不适合 Conan 打包），改为手动拷贝头文件/库并创建相对符号链接。
- R32: settings.os 判断使用 ("Linux", "OHOS")。
- R33: 编译器/标志经 GnuToolchain 从 Conan profile 注入，不裸用 shell 变量。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, chdir, \
    apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class LibexecinfoConan(ConanFile):
    name = "libexecinfo"
    version = "20180201"
    description = "BSD clone of the GNU backtrace facility (execinfo.h) for non-glibc platforms"
    license = "BSD-2-Clause"
    homepage = "https://github.com/resslinux/libexecinfo"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported (Linux/OHOS only)")
        if self.settings.os == "OHOS" and self.settings.arch not in ("armv8", "arm64"):
            raise ConanInvalidConfiguration(
                f"OHOS arch={self.settings.arch} not supported (armv8 only)")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # R33: 通过 GnuToolchain 注入 CC/CFLAGS 等（来源 Conan profile/conf）
    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        with chdir(self, self.source_folder):
            # R9: -j1 避免并行竞态；Makefile 直接生成 .a/.so.1
            self.run("make -j1")

    def package(self):
        copy(self, "execinfo.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "stacktraverse.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "libexecinfo.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "libexecinfo.so.1", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        # 相对符号链接（上游 make install 硬编码 /usr/lib 绝对路径，不适合打包）
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared and os.path.exists(os.path.join(libdir, "libexecinfo.so.1")):
            link = os.path.join(libdir, "libexecinfo.so")
            if os.path.islink(link) or os.path.exists(link):
                os.unlink(link)
            os.symlink("libexecinfo.so.1", link)

    def package_info(self):
        self.cpp_info.libs = ["execinfo"]
