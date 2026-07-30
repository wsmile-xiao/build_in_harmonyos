#!/usr/bin/env python3
"""Conan recipe for grepcidr 2.0 — CIDR pattern filtering tool.

grepcidr is a command-line tool that filters IPv4/IPv6 addresses
matching CIDR/network specifications. It is a single-file C program
with a simple Makefile (no configure step).

On HarmonyOS (OHOS), ELF binaries must be signed before execution.
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GrepcidrConan(ConanFile):
    name = "grepcidr"
    version = "2.0"
    description = "Filter IPv4/IPv6 addresses matching CIDR patterns"
    license = "GPL-2.0-or-later"
    homepage = "https://www.pc-tools.net/unix/grepcidr/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        # R33: Get compiler from Conan conf, not undefined shell variables
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("c") or "clang"

    def _sign_elf(self, path):
        """Sign ELF binary on OHOS for execution on HarmonyOS."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if Path(sign_tool).exists():
            self.run(f"{objcopy} --remove-section .codesign {path} || true")
            self.run(f"{sign_tool} sign -inFile {path} -outFile {path}.signed -selfSign 1")
            shutil.move(f"{path}.signed", path)
        os.chmod(path, 0o755)

    def build(self):
        apply_conandata_patches(self)
        cc = self._get_cc()
        self.run(f"make CC={cc} CFLAGS='-O2 -Wall' -j1", cwd=self.source_folder)

        # Sign the binary on OHOS so test_package can execute it
        if self.settings.os == "OHOS":
            bin_path = os.path.join(self.source_folder, "grepcidr")
            self._sign_elf(bin_path)

    def package(self):
        copy(self, "grepcidr", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "grepcidr.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
