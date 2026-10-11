#!/usr/bin/env python3
"""Conan recipe for pagein 0.01.11 - force pages of running processes into RAM.

Upstream is a single C file with a hand-written Makefile and no third-party
dependencies.  pagein walks a process' address space (or all processes) and
touches every mapped page so the pages are paged in; it needs CAP_SYS_PTRACE
(or root) to attach to the target, so the installed-program checks here only
cover the presence and the argument/usage error paths.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout


class PageinConan(ConanFile):
    name = "pagein"
    version = "0.01.11"
    description = "Force pages of running processes to be paged in"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ColinIanKing/pagein"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pagein OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        self.run('make CC="{}" -j1'.format(cc), cwd=self.source_folder)
        if not os.path.isfile(os.path.join(self.source_folder, "pagein")):
            raise ConanInvalidConfiguration("build did not produce the 'pagein' program")

    def package(self):
        copy(self, "pagein", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "pagein.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "pagein", os.path.join(self.source_folder, "bash-completion"),
             os.path.join(self.package_folder, "share", "bash-completion", "completions"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README*", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
