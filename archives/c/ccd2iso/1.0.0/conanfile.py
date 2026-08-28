#!/usr/bin/env python3
"""Conan recipe — ccd2iso 1.0.0 (Autotools).

CloneCD image (.img) to ISO 9660 image file converter.
Source fixes applied via replace_in_file() in build():
- ccd2iso.c missing <string.h> (uses strcmp/strlen without include)
- configure umask 077 -> 022 (OHOS sandbox creates 0700 temp dirs)
- configure as_expr=false (OHOS toybox expr '\|' chain bug, sed fallback)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Ccd2isoConan(ConanFile):
    name = "ccd2iso"
    version = "1.0.0"
    description = "CloneCD image (.img) to ISO 9660 image file converter"
    license = "GPL-2.0"
    homepage = "https://ccd2iso.sourceforge.net/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        # AutotoolsToolchain 只导出 CFLAGS/CXXFLAGS/LDFLAGS，不导出 CC——
        # configure 检查 gcc/cc 失败（"no acceptable C compiler"）。
        # 显式注入 CC/CXX 绝对路径（沙箱裸 clang 查找失败先例）。
        from conan.tools.env import Environment
        env = Environment()
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        env.define("CC", compilers.get("c", "clang"))
        env.define("CXX", compilers.get("cpp", "clang++"))
        env.vars(self).save_script("conanbuild_cc")

    def build(self):
        apply_conandata_patches(self)

        # Fix 1: ccd2iso.c - missing <string.h> (uses strcmp/strlen)
        src_c = os.path.join(self.source_folder, "src", "ccd2iso.c")
        replace_in_file(self, src_c, "#include <stdlib.h>\n",
                        "#include <stdlib.h>\n#include <string.h>\n")

        # Fix 2: configure - umask 077 creates 0700 temp dirs (setgid without
        # group execute) on OHOS, preventing file creation (librrd 先例)
        conf = os.path.join(self.source_folder, "configure")
        replace_in_file(self, conf, "umask 077", "umask 022")

        # Fix 3: configure - OHOS toybox expr 0.8.12 '\|' multi-branch chain
        # bug pollutes config.status ac_dir extraction; force sed fallback
        replace_in_file(self, conf, "as_expr=expr", "as_expr=false")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
