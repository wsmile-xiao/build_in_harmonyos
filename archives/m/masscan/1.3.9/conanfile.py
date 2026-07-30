#!/usr/bin/env python3
"""Conan recipe for masscan — the fastest internet port scanner.

masscan uses a plain Makefile (no configure script). This recipe
builds the masscan binary with appropriate OHOS platform patches.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class MasscanConan(ConanFile):
    name = "masscan"
    version = "1.3.9"
    description = "masscan: the fastest internet port scanner"
    license = "AGPL-3.0"
    homepage = "https://github.com/robertdavidgraham/masscan"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # masscan uses a plain Makefile — no toolchain generation needed
        pass

    def build(self):
        apply_conandata_patches(self)
        # masscan has no configure script — run make from source root
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Copy the built binary from the source folder
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "masscan", src=os.path.join(self.source_folder, "bin"),
             dst=bindir)

    def package_info(self):
        # masscan is a command-line tool, not a library
        self.cpp_info.bindirs = ["bin"]
