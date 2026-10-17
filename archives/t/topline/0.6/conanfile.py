#!/usr/bin/env python3
"""Conan recipe — topline 0.6 (upstream plain Makefile, top-like IO monitor CLI).

Upstream ships no configure script and no test suite; the Makefile hardcodes
CC=gcc, which does not exist on the OHOS toolchain, so the C compiler is
passed explicitly from Conan's tools.build:compiler_executables. The single
artifact is the `topline` binary.
"""
import os

from conan import ConanFile
from conan.tools.build import build_jobs
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class ToplineConan(ConanFile):
    name = "topline"
    version = "0.6"
    description = "topline — interactive, programmable, top-like IO monitor"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/kilobyte/topline"
    url = ""  # CI fills this
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        jobs = build_jobs(self)
        self.run(
            f"make -j{jobs} CC={cc} CFLAGS='-Wall -O2'",
            cwd=self.source_folder,
        )

    def package(self):
        copy(
            self,
            "topline",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
