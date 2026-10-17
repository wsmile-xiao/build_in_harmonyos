#!/usr/bin/env python3
"""Conan recipe — libstatgrab 0.92.1 (Autotools).

libstatgrab is an autotools library exposing system statistics APIs
(host/cpu/memory/load/fs/disk/network/process stats).

OHOS adaptation:
  * OHOS 的 config.guess（2018）无法识别 HarmonyOS kernel，configure 报
    "cannot guess build type"；与 liblhasa/lib3ds 同策略，显式传
    --build/--host=aarch64-unknown-linux-gnu（ABI 层面等价 Linux-ELF）。
  * 构建期将 configure 内的 `umask 077` 替换为 `umask 022`：OHOS 受限
    文件系统下 config.status 用 umask 077 建临时目录后写入会被拒
    （"Permission denied: subs1.awk"）。
  * 恢复 config.guess/config.sub/install-sh/missing/configure 的可执行位
    （E490：OHOS/HMDFS 路径可能不保留 execute bit）。
"""
import os

from conan import ConanFile
from conan.tools.files import (get, apply_conandata_patches,
                               export_conandata_patches, chmod)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibstatgrabConan(ConanFile):
    name = "libstatgrab"
    version = "0.92.1"
    description = "libstatgrab 0.92.1"
    license = "LGPL-2.1-or-later"
    homepage = "https://libstatgrab.org/"
    url = "https://github.com/libstatgrab/libstatgrab"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # OHOS: config.guess 无法识别 HarmonyOS kernel，显式指定 build/host
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        pas = os.path.join(self.build_folder, os.pardir)
        # E490: 恢复 autotools 脚本可执行位（OHOS/HMDFS 可能丢失 execute bit）
        for helper in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing"):
            p = os.path.join(pas, helper)
            if os.path.exists(p):
                chmod(self, p, 0o755)
        # OHOS: config.status 的 umask 077 临时目录写入被拒，改为 022
        self.run("sed -e 's/umask 077/umask 022/g' -i configure",
                 cwd=pas, env="conanbuild")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 库文件为 libstatgrab.a（链接标志 -lstatgrab），CMakeDeps 会加
        # lib 前缀与后缀查找，故声明 "statgrab" 而非 "libstatgrab"
        self.cpp_info.libs = ["statgrab"]
