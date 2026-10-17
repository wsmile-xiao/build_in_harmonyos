#!/usr/bin/env python3
"""Conan recipe — dis51 0.5 (plain Makefile)

dis51 is an 8051 microcontroller disassembler: it reads an Intel HEX file
from stdin and writes 8051 assembly language to stdout, following the code
from the entry points given on the command line.

Version 0.5 (21 Nov 2003) is a plain-Makefile C program: no configure script,
no install target and no upstream test suite.  The recipe therefore builds
with the compiler from the Conan profile and installs the resulting binary
into bin/ explicitly.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class Dis51Conan(ConanFile):
    name = "dis51"
    version = "0.5"
    description = "8051 disassembler for Intel HEX files (reads HEX from stdin, writes 8051 assembly to stdout)"
    license = "GPL-2.0-only"
    homepage = "https://plit.de/asem-51/dis51.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: the tool is a plain POSIX C program, only Linux/OHOS are supported.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux and OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: take the compiler from the Conan profile, never from a bare
        # ${CC} in the shell environment.
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c") or "clang"
        # R9: a five-object Makefile project — keep the build single job.
        self.run(f'make -j1 CC="{cc}"', cwd=self.source_folder)

    def package(self):
        copy(self, "dis51", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
