#!/usr/bin/env python3
"""Conan recipe — clac 0.3.5 (plain makefile).

clac is a command-line, stack-based calculator with postfix notation.
Build system: plain makefile (no configure script). linenoise and sds are
vendored under deps/ in the official tarball and built by the top makefile.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class ClacConan(ConanFile):
    name = "clac"
    version = "0.3.5"
    description = "Command-line, stack-based calculator with postfix notation"
    license = "BSD-2-Clause"
    homepage = "https://github.com/soveran/clac"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"clac supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        comp = self.conf.get(
            "tools.build:compiler_executables", check_type=dict, default={}
        )
        cc = comp.get("c", "clang") if comp else "clang"
        src = self.source_folder
        # No configure step; CC must be passed explicitly (the OHOS host has no
        # `cc`) and propagates to the vendored linenoise/sds sub-makes.
        self.run(f"make -j1 CC='{cc}'", env="conanbuild", cwd=src)

    def package(self):
        src = self.source_folder
        # The makefile install target runs strip and assumes a system PREFIX;
        # copy the built artifacts directly instead.
        copy(self, "clac", src=src,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "clac.1", src=src,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
