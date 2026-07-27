#!/usr/bin/env python3
"""Conan recipe for cidrmerge 1.5.3 — CIDR merging command-line tool.

cidrmerge is a pure C program with a simple Makefile (no configure, no make install).
Build output: a single 'cidrmerge' binary.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CidrmergeConan(ConanFile):
    name = "cidrmerge"
    version = "1.5.3"
    description = "CIDR merging with network exclusion - CIDR 地址优化工具"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/cidrmerge/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # R9: Always use -j1
        # The Makefile uses CC, STD_DEFINES, CC_FLAGS, LINK_FLAGS
        # We only override CC to use the Conan-provided compiler
        src = self.source_folder
        self.run(f"make -C {src} CC={cc} -j1")

    def package(self):
        # Copy the binary to bin/
        copy(self, "cidrmerge", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Copy header for library integration
        copy(self, "cidrmerge.h", self.source_folder, os.path.join(self.package_folder, "include"))

    def package_info(self):
        # Application: binary in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
