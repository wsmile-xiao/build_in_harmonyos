#!/usr/bin/env python3
"""Conan recipe for texi2html 5.0 — GNU Texinfo→HTML 转换工具（Perl 实现）。

上游：https://download-mirror.savannah.gnu.org/releases/texi2html/texi2html-5.0.tar.gz
构建：Perl ExtUtils::MakeMaker（perl Makefile.PL + make + make test + make install，
      arch=all 无编译）
依赖：perl/5.42.2（ohpcd 已合入）+ 核心模块（Getopt::Long 等 perl 自带）
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class Texi2htmlConan(ConanFile):
    name = "texi2html"
    version = "5.0"
    description = "texi2html — Texinfo to HTML converter (GNU, Perl implementation)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/texi2html/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # texi2html 5.0 源码包无 Makefile.PL（非 ExtUtils::MakeMaker 构建）——
        # texi2html.pl 是主脚本（Perl 实现，arch=all），无需编译，直接分发
        pass

    def package(self):
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 主脚本 + 生成的 texi2html 可执行文件
        for exe in ("texi2html", "texi2html.pl", "texi2html.py"):
            copy(self, exe, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
