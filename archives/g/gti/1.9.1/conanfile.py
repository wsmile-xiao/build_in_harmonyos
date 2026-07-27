#!/usr/bin/env python3
"""Conan recipe — gti 1.9.1 (git launcher with ASCII art car animation).

Makefile project (raw make, no configure).
Produces a single binary `gti` that shows a VW Golf GTI animation
when you mistype `git`, then delegates to the real git command.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GtiConan(ConanFile):
    name = "gti"
    version = "1.9.1"
    description = "A git launcher that shows an ASCII art car animation when you mistype 'git'"
    license = "MIT"
    homepage = "https://github.com/rwos/gti"
    url = "https://github.com/rwos/gti"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: Use `in ("Linux", "OHOS")` for settings.os check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gti supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # R9: Always use -j1
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "gti", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
