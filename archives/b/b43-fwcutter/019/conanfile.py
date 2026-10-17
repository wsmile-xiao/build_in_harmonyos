#!/usr/bin/env python3
"""Conan recipe for b43-fwcutter 019 — Broadcom 43xx firmware extraction tool.

b43-fwcutter is a tool to extract firmware from binary Broadcom 43xx wireless
driver files. The extracted firmware is used by the open-source b43/b43legacy
Linux wireless drivers.

Build system: simple Makefile (no configure, no autotools, no cmake).
License: BSD 2-clause.
No external library dependencies — only standard C library.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class B43FwcutterConan(ConanFile):
    name = "b43-fwcutter"
    version = "019"
    description = "Tool for extracting Broadcom 43xx wireless driver firmware"
    license = "BSD-2-Clause"
    homepage = "https://bues.ch/b43/fwcutter/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not shell env vars.
        # CFLAGS/LDFLAGS come from profile buildenv (sysroot, code-sign, etc.)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # R9: Always use -j1
        self.run(f"make -j1 CC={cc}")

    def package(self):
        # Manual install — the Makefile's `install` target uses `install -o 0 -g 0`
        # which may fail on OHOS. Copy files manually instead.
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(man_dir, exist_ok=True)

        src_bin = os.path.join(self.source_folder, "b43-fwcutter")
        src_man = os.path.join(self.source_folder, "b43-fwcutter.1")
        shutil.copy2(src_bin, os.path.join(bin_dir, "b43-fwcutter"))
        shutil.copy2(src_man, os.path.join(man_dir, "b43-fwcutter.1"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
