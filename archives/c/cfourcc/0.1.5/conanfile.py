#!/usr/bin/env python3
"""Conan recipe for cfourcc — a single-file C CLI tool to change the FOURCC
of MPEG4/DivX AVI files. Builds with the upstream Makefile (CC-driven,
single cfourcc.c source, no configure, no external deps, no test suite).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class CfourccConan(ConanFile):
    name = "cfourcc"
    version = "0.1.5"
    description = "UNIX/Linux tool for changing the FOURCC of an MPEG4 or DivX AVI file"
    license = "GPL-2.0"
    homepage = "https://github.com/mypapit/cfourcc"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R33: get compiler from Conan conf (dict), never ${CC} shell env (empty on CI)
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # R9: always -j1, never -j$(nproc)
        # basic_layout puts cwd in build-release/ — run make in the source
        # folder where the upstream Makefile lives (same as altermite recipe)
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # cfourcc is a standalone CLI binary (package_type=application), no libs/headers.
        # Upstream `make install` uses $(INSTALL) -D + strip + PREFIX; simpler & safer
        # to copy the built binary directly into the package bin/.
        copy(self, "cfourcc", self.source_folder,
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
