#!/usr/bin/env python3
"""Conan recipe — rcm 1.3.6-r0 (upstream v1.3.6) — Autotools build system.

rcm is a dotfile management tool suite providing rcup, rcdn, lsrc, mkrc.
It is a pure shell-script application (no C compilation).
Source: https://github.com/thoughtbot/rcm
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RcmConan(ConanFile):
    name = "rcm"
    version = "1.3.6-r0"
    description = "rc file (dotfile) management — manage dotfiles with rcup, rcdn, lsrc, mkrc"
    license = "BSD-3-Clause"
    homepage = "https://github.com/thoughtbot/rcm"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rcm supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        get(self, **sources, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # rcm 的 configure.ac 无 AC_CANONICAL_HOST，不做平台检测，
        # 不需要 --build 或 --host 参数
        tc.generate()

    def build(self):
        if self.settings.os in ("OHOS",):
            src = self.source_folder
            configure_path = os.path.join(src, "configure")
            # E165: Fix shebang (no /bin/sh on OHOS)
            replace_in_file(self, configure_path, "#! /bin/sh", "#!/system/bin/sh")
            # E110: Fix umask 077->002 for HMDFS temp directory creation
            replace_in_file(self, configure_path, "umask 077", "umask 002")
            # E165: Fix bin/*.in shebang
            # All bin/*.in use #!@SHELL@ which configure replaces with $SHELL (/bin/sh).
            # Replace directly so generated scripts have a valid OHOS shebang.
            for script in ("lsrc", "mkrc", "rcdn", "rcup"):
                replace_in_file(self, os.path.join(src, "bin", f"{script}.in"),
                                "#!@SHELL@", "#!/data/service/hnp/bin/bash")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # L1c: 运行上游官方测试 (make check)
        # rcm 使用 cram 框架 (LOG_COMPILER=cram)，OHOS 可能未安装 cram
        cram = shutil.which("cram")
        if cram:
            autotools.make(target="check")
        else:
            self.output.warning("cram not found, skipping upstream tests (make check)")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # rcm is a CLI shell-script application, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
