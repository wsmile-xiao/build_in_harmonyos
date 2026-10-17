#!/usr/bin/env python3
"""Conan recipe — vbrfix 0.24（vbrfixc，命令行 MP3 VBR 头修复工具）

VBRfix 命令行版：扫描 MP3，重建 VBR 头（Xing/Info），修正错误的比特率、
时长与 seek 信息。纯 C++，无第三方依赖；上游构建系统为 KDE/KDevelop
生成的 autotools（configure + make）。

产物为命令行可执行文件 bin/vbrfixc → 软件级目录需 commands.json（R38）。
"""
import os

from conan import ConanFile
from conan.tools.files import (get, copy, apply_conandata_patches,
                               export_conandata_patches)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class VbrfixConan(ConanFile):
    name = "vbrfix"
    version = "0.24"
    description = ("VBRfix (vbrfixc) — scans MP3 files and rebuilds a correct "
                   "VBR header (Xing/Info), fixing wrong bitrate, duration and "
                   "seek information")
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/vbrfix"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # E490：HMDFS 下 conan 把源码复制到 build 目录时可能丢失 POSIX 执行位，
    # 导致 configure 以 126 (Permission denied) 失败。构建前为已知 autotools
    # 辅助脚本补回执行位。
    _AUTOTOOLS_HELPERS = (
        "configure", "config.guess", "config.sub", "install-sh", "missing",
        "mkinstalldirs", "depcomp", "compile", "ylwrap", "ltmain.sh",
        "admin/config.guess", "admin/config.sub", "admin/install-sh",
        "admin/missing", "admin/mkinstalldirs", "admin/depcomp",
        "admin/compile", "admin/ylwrap", "admin/ltmain.sh",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R1：参数最少化 —— 上游 configure 只需要 --prefix（由 Toolchain 生成）。
        # 本包为纯可执行文件，无共享/静态库选项。
        tc = AutotoolsToolchain(self)
        self._configure_args = list(tc.configure_args)
        tc.generate()

    def _restore_exec_bits(self):
        for root in {self.source_folder, self.build_folder}:
            if not root:
                continue
            for rel in self._AUTOTOOLS_HELPERS:
                path = os.path.join(root, rel)
                if os.path.isfile(path):
                    try:
                        os.chmod(path, os.stat(path).st_mode | 0o111)
                    except OSError:
                        pass

    def build(self):
        apply_conandata_patches(self)
        self._restore_exec_bits()
        # OHOS/HMDFS：conan 复制源码到 build 目录后，新建脚本文件在 execve 时
        # 返回 EACCES（chmod +x 也无效，先例：autofs 5.1.9 / automake 1.19 配方
        # 均注明 "run configure via sh(1)"），直接执行 configure 报
        # "126 Permission denied"。改由 sh 显式解释执行，参数与
        # Autotools.configure() 一致（来自 AutotoolsToolchain）。
        configure = os.path.join(self.source_folder, "configure")
        args = " ".join("'%s'" % a for a in self._configure_args)
        self.run('/bin/sh "%s" %s' % (configure, args), env="conanbuild")
        autotools = Autotools(self)
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.buildenv_info.append_path("PATH", bin_path)
            self.runenv_info.append_path("PATH", bin_path)
