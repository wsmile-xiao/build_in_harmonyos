#!/usr/bin/env python3
"""Conan recipe for libobjfwhid1 1.5.7 — ObjFW's HID / game controller library.

Builds the whole ObjFW source tree (Autotools), which produces libobjfw,
libobjfwrt and libobjfwhid. libobjfwhid's Linux backend uses evdev
(linux/input.h, sys/ioctl.h, fcntl.h, errno.h); no external conan deps.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

import os
import shutil
import stat


class Libobjfwhid1Conan(ConanFile):
    name = "libobjfwhid1"
    version = "1.5.7"
    description = "ObjFWHID — ObjFW's HID/game controller library (Objective-C, evdev backend)"
    license = "LGPL-3.0"
    homepage = "https://objfw.nil.im/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Self-contained: no external dependencies (W0 verified).
        pass

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libobjfwhid1 supports Linux/OHOS targets, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        # ObjFW 的各级 Makefile（顶层/src/tests/utils）是发行版 tarball 携带的
        # 静态文件，非 automake/configure 生成 → 必须在源码目录内 in-source 构建，
        # 否则 out-of-tree build 目录无 Makefile（"No targets specified and no
        # makefile found"）。与仓库其他 in-source autotools 配方同构。
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # No TLS backend available on OHOS; HID does not need TLS.
        tc.configure_args.append("--without-tls")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def _restore_autotools_helper_modes(self):
        # E490 (restore-known-autotools-script-modes): 上游 objfw-1.5.7.tar.gz 的
        # build-aux/config.guess 与 build-aux/config.sub 未携带执行位（tar 内为
        # -rw-rw-r--），HMDFS 传输/解压后仍会以 "Permission denied" 拒绝执行，导致
        # configure 系统探测阶段直接失败。按 E490 方案在 configure 前对已知 helper
        # 逐个 chmod +x（禁止 chmod -R +x，避免隐藏元数据问题）。`missing` 本包源码
        # 树不存在，os.path.exists 守卫保证逐个跳过、不报错。
        helpers = ["configure", "config.guess", "config.sub", "install-sh", "missing"]
        for base in (self.source_folder, os.path.join(self.source_folder, "build-aux")):
            for name in helpers:
                path = os.path.join(base, name)
                if os.path.exists(path):
                    mode = os.stat(path).st_mode
                    os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # E490: configure 前先恢复 autotools helper 执行位（config.guess/config.sub/
        # install-sh/missing/configure 逐个 chmod +x），否则系统探测阶段 Permission denied。
        self._restore_autotools_helper_modes()
        autotools.configure()
        # E074: 本机 HMDFS 上 make -jN 的 jobserver mkfifo（TMPDIR）会
        # "Operation not permitted"，与仓库其他 autotools 配方一致用 -j1。
        autotools.make(args=["-j1"])
        # E490/E074: 同族 autotools 配方（libXt/libXext 等）惯例在 build() 内跑上游
        # make check，本包同样以 -j1 执行（上游实测 1238 通过 / 0 失败 / 4 跳过，exit 0）。
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Library package: drop the ObjFW dev/utility executables so the
        # package stays a pure library (R38: library type, no commands.json).
        for sub in ("bin", "sbin"):
            d = os.path.join(self.package_folder, sub)
            if os.path.isdir(d):
                shutil.rmtree(d)

    def package_info(self):
        # ObjFWHID depends on libobjfw which depends on libobjfwrt.
        self.cpp_info.libs = ["objfwhid", "objfw", "objfwrt"]
