#!/usr/bin/env python3
"""Conan recipe for scsi-tgt v1.0 — SCSI target framework (Makefile project).

scsi-tgt (tgt) is a SCSI target framework for Linux/OpenHarmony.
It provides tgtd (daemon), tgtadm (admin tool), and tgtimg (image tool).
Build system: plain Makefile (no configure script needed).
Output: usr/tgtd, usr/tgtadm, usr/tgtimg (command-line tools, not libraries).

Platform compatibility:
  - pthread_cancel replaced with stop-flag pattern (musl compatibility)
  - strict-prototypes warnings fixed for -Werror
  - doc/Makefile patched for xsltproc absence
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class ScsiTgtConan(ConanFile):
    name = "scsi-tgt"
    version = "v1.0"
    description = "SCSI target daemon and administration tool"
    license = "GPL-2.0"
    homepage = "https://github.com/fujita/tgt"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Create configure script (Makefile-only project needs it for build framework)
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure_path):
            with open(configure_path, "w") as f:
                f.write("#!/bin/sh\nexit 0\n")

        # R33: Get compiler from Conan conf, not from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # R9: Always use -j1 for reliability
        self.run(f"make CC={cc} -j1")

    def package(self):
        src_usr = os.path.join(self.source_folder, "usr")
        copy(self, "tgtd", src=src_usr, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "tgtadm", src=src_usr, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "tgtimg", src=src_usr, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
