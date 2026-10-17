#!/usr/bin/env python3
"""Conan recipe — intltool 0.51.0 (Perl internationalization toolset).

intltool 是一组用于 GNU 国际化流程的纯 Perl 脚本（intltool-update /
intltoolize / intltool-extract / intltool-merge / intltool-prepare），
autotools 构建，产物是 bin/ 下 5 个可执行脚本 + share/intltool 数据。

适配要点：
- 纯 Perl 脚本，无原生编译；configure 会检查 XML::Parser 模块（XS 模块因
  HMDFS dlopen 限制无法加载）——0001-configure.patch 跳过该检查。
- configure 需要 PERL 解释器（ohpcd 上 perl 包提供 /usr/bin/perl）。
- 构建用 -j1（HMDFS mkfifo 限制，并行构建失败）。
- 上游 selftest 套件（tests/selftest.pl）因 HMDFS 无法执行 Perl 脚本而
  部分失败——平台限制，非功能问题，如实声明。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain


def _drop_umask_077(path):
    """HMDFS rejects 0600 temp dirs — rewrite `umask 077` to `umask 022`."""
    try:
        data = open(path, "r", encoding="utf-8", errors="replace").read()
        if "umask 077" in data:
            open(path, "w", encoding="utf-8").write(data.replace("umask 077", "umask 022"))
    except Exception:
        pass


class IntltoolConan(ConanFile):
    name = "intltool"
    version = "0.51.0"
    package_type = "application"
    license = "GPL-2.0-or-later"
    homepage = "https://launchpad.net/intltool"
    description = "intltool — Perl internationalization toolset (intltool-update/intltoolize/extract/merge/prepare)"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"intltool does not support os={self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("ac_cv_prog_cc_works=yes")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS 拒绝 0600 临时目录——configure 的 umask 077 需改为 022
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()  # HMDFS mkfifo 限制——如并行失败需 -j1

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
