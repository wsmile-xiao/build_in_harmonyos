#!/usr/bin/env python3
"""Conan test_package for qt-mariadb 5.15.2.

Compiles test_plugin.c and runs it against the built plugin
(plugins/sqldrivers/libqsqlmysql.so). The test parses the plugin
ELF image directly — runtime dlopen is not possible on OHOS
without ELF signing (platform limitation, see notes.md), so the
plugin is validated by inspecting its binary contents: driver
keys (QMYSQL/QMARIADB), libmariadb linkage, and Qt plugin
interface exports.
"""
import os

from conan import ConanFile


class QtMariadbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or compilers.get("cc") or "clang"
        src = os.path.join(self.source_folder, "test_plugin.c")
        self.run(f'"{cc}" -O2 -o test_plugin "{src}"')

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        so_path = os.path.join(pkg, "plugins", "sqldrivers", "libqsqlmysql.so")
        assert os.path.isfile(so_path), f"Plugin not found: {so_path}"
        print(f"[OK] Plugin found: {so_path}")
        self.run(f'"./test_plugin" "{so_path}"')
