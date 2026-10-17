#!/usr/bin/env python3
"""Conan recipe — outils 0.14

outils: port of some non-standard OpenBSD tools to Linux
(apply, calendar, cksum/md5/sha*, jot, lam, lndir, rdate, rs, signify,
ts, unvis, vis, what).  Pure hand-written Makefile project, no configure
script; all tools are self-contained (libc + bundled portability code,
LIBS=-lm only).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

TOOLS = [
    ("apply", "src/usr.bin/apply"),
    ("calendar", "src/usr.bin/calendar"),
    ("jot", "src/usr.bin/jot"),
    ("lam", "src/usr.bin/lam"),
    ("lndir", "src/usr.bin/lndir"),
    ("md5", "src/bin/md5"),
    ("rdate", "src/usr.sbin/rdate"),
    ("rs", "src/usr.bin/rs"),
    ("signify", "src/usr.bin/signify"),
    ("ts", "src/usr.bin/ts"),
    ("unvis", "src/usr.bin/unvis"),
    ("vis", "src/usr.bin/vis"),
    ("what", "src/usr.bin/what"),
]

# md5 按 argv[0] 分派 cksum/sha1/sha256/sha512 行为（上游用 ln -s 安装）
MD5_ALIASES = ["cksum", "sha1", "sha256", "sha512"]


class OutilsConan(ConanFile):
    name = "outils"
    version = "0.14"
    description = ("Port of some non-standard OpenBSD tools to Linux "
                   "(apply, calendar, cksum/md5/sha*, jot, lam, lndir, rdate, "
                   "rs, signify, ts, unvis, vis, what)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/leahneukirchen/outils"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器从 Conan conf 获取，不依赖 shell 环境变量
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(compilers, dict):
            cc = compilers.get("c", "clang")
        else:
            cc = "clang"

        # R9: -j1；Makefile 自带 CPPFLAGS/LDFLAGS/LIBS，无需额外参数
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        bin_dst = os.path.join(self.package_folder, "bin")
        for tool, subdir in TOOLS:
            copy(self, tool, os.path.join(self.source_folder, subdir), bin_dst)

        # 以真实副本安装 md5 别名：行为与上游软链接一致（argv[0] 分派），
        # 且规避 HMDFS 上软链接的兼容性问题
        md5_bin = os.path.join(bin_dst, "md5")
        for alias in MD5_ALIASES:
            shutil.copy2(md5_bin, os.path.join(bin_dst, alias))

        man_dst = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "*.1", os.path.join(self.source_folder, "src"), man_dst,
             keep_path=False)
        for alias in ("sha1", "sha256", "sha512"):
            shutil.copy2(os.path.join(man_dst, "md5.1"),
                         os.path.join(man_dst, alias + ".1"))

        # calendar 数据文件（上游独立的 install-calendars 目标）
        copy(self, "*",
             os.path.join(self.source_folder, "src", "usr.bin", "calendar", "calendars"),
             os.path.join(self.package_folder, "share", "calendar"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
