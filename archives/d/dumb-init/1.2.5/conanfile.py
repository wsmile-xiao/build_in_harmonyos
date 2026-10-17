#!/usr/bin/env python3
"""Conan recipe for dumb-init 1.2.5 — minimal init system for Linux containers.

dumb-init is a simple process supervisor and init system designed to run as
PID 1 inside minimal container environments. It is a single C file (~340 lines)
compiled to a static binary with no external dependencies.

Build system: raw Makefile (no configure script).
Output: a single static binary (dumb-init).

R33: Compiler obtained from Conan conf, not shell env vars.
R38: Command-line tool — commands.json declared at software level.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DumbInitConan(ConanFile):
    name = "dumb-init"
    version = "1.2.5"
    description = "A minimal init system for Linux containers"
    license = "MIT"
    homepage = "https://github.com/Yelp/dumb-init"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take toolchain paths from Conan conf, never from shell env.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        self.run(f"make build CC={cc} -j1")

    def package(self):
        copy(self, "dumb-init", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
