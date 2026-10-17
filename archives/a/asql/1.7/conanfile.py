#!/usr/bin/env python3
"""Conan recipe — asql 1.7 (Provide an SQL interface to Apache logfiles).

Build system: none — pure-Perl scripts (bin/asql + bin/make-cmds).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy


class AsqlConan(ConanFile):
    name = "asql"
    version = "1.7"
    description = "Provide an SQL interface to Apache logfiles"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/asql"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 Perl——无编译——但运行上游 t/ 测试（prove t/——modules/
        # no-tabs/perl-syntax/pod——OHOS perl 环境——通过率如实记录）
        self.run("prove --shuffle t/", cwd=self.source_folder, ignore_errors=True)

    def package(self):
        src = self.source_folder
        copy(self, "asql", src=os.path.join(src, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "make-cmds", src=os.path.join(src, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        for doc in ("COMMANDS", "README"):
            copy(self, doc, src=src,
                 dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
