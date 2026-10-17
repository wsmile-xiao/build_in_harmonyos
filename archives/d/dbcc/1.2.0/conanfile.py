#!/usr/bin/env python3
"""Conan recipe — dbcc 1.2.0

dbcc: CAN DBC to C (and CSV, JSON, XML, BSM) compiler, uses the mpc parser
combinator library (vendored in-tree). Plain-Makefile project: no configure
script, no `install` target; `make` produces the `dbcc` executable.

Build system: plain Makefile (lowercase `makefile`), no configure.
License: MIT
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DbccConan(ConanFile):
    name = "dbcc"
    version = "1.2.0"
    description = "CAN DBC to C (and CSV, JSON and XML) compiler"
    license = "MIT"
    homepage = "https://github.com/howerj/dbcc"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # R9: always -j1
        self.run(f'make -j1 CC="{cc}"', cwd=self.source_folder)

    def package(self):
        # Command-line tool: install the binary to bin/
        copy(self, "dbcc", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]