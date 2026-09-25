#!/usr/bin/env python3
"""Conan recipe for s-nail 14.9.25 -- a MIME-capable mailx(1) command (BSD mail
successor).  Build system is s-nail's own make(1) framework: `make config`
performs fully non-interactive feature detection, then `make` builds the
`s-nail` executable in .obj/.  No external library is required by default;
optional features (OpenSSL/TLS, IDNA, GSSAPI) are auto-disabled when their
libraries are absent, which is the case on OHOS.
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SNailConan(ConanFile):
    name = "s-nail"
    version = "14.9.25"
    description = "s-nail: a MIME-capable mailx(1) command (modern Berkeley mail)"
    license = ("ISC AND BSD-2-Clause AND BSD-3-Clause AND LGPL-2.1-or-later")
    homepage = "https://www.sdaoden.eu/code-nail.html"
    url = "https://ftp.sdaoden.eu/s-nail-14.9.25.tar.xz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 无缺省硬依赖：libc(含 iconv/regex) 即可；openssl/libidn 等可选特性
        # 由 `make config` 自动探测并禁用（上游缺省不 require 任何特性）。
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        return compilers.get("c", "clang") if compilers else "clang"

    # s-nail `make config` 探测 chown(1)/cksum(1) 等工具；鸿蒙设备的工具集在
    # /system/bin(toybox)，未包含在构建环境的 PATH 里，需追加。
    def _with_path(self, cmd):
        return f'PATH="$PATH:/system/bin" {cmd}'

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        cc = self._cc()
        makevars = f"CC={cc} OPT_DOTLOCK=no"

        # 1) 非交互配置（特性自动探测；HarmonyOS 被上游 os_setup 识别）
        self.run(self._with_path(f"make {makevars} config"), cwd=src)
        # 2) 构建（R9: -j1；产物在 .obj/s-nail）
        self.run(self._with_path(f"make {makevars} -j1"), cwd=src)
        # 3) 上游测试套件（mx-test.sh --check，套件自身计数）：
        #    OHOS/HMDFS 文件系统限制导致的少量环境性失败不阻断配方构建，
        #    计数以日志汇总行 "N tests: x ok, y failure(s). z test(s) skipped"
        #    为准并如实申报（见 notes.md 与 PR 正文）。
        self.run(self._with_path(f"make {makevars} testnj || true"), cwd=src)

    def package(self):
        src = self.source_folder
        obj = os.path.join(src, ".obj")
        copy(self, "s-nail", obj, os.path.join(self.package_folder, "bin"))
        copy(self, "s-nail.rc", src,
             os.path.join(self.package_folder, "etc"))
        man1 = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "uman.1", obj, man1)
        if os.path.exists(os.path.join(man1, "uman.1")):
            os.rename(os.path.join(man1, "uman.1"),
                      os.path.join(man1, "s-nail.1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
