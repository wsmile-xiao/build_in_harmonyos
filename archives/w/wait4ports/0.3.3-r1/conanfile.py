#!/usr/bin/env python3
"""Conan recipe for wait4ports — a small utility to wait for network peer availability.

wait4ports is a command-line tool (not a library). It builds a single binary
from main.c and list.c using a simple Makefile (no configure step).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Wait4PortsConan(ConanFile):
    name = "wait4ports"
    version = "0.3.3-r1"
    description = "A small utility to wait for network peer availability"
    license = "MPL-2.0"
    homepage = "https://github.com/erikogan/wait4ports"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not shell env vars
        compiler_executables = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        # R9: Use -j1; build in source folder where Makefile lives
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # wait4ports is a binary tool — copy the executable to bin/
        copy(self, "wait4ports", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
