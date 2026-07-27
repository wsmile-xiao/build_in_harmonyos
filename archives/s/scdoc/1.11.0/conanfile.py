#!/usr/bin/env python3
"""Conan recipe for scdoc 1.11.0 — simple man page composer.

scdoc is a C program that converts a simple markup language to man pages.
It uses a plain Makefile (no configure), produces a single static executable.

Platform compatibility:
  - Patches fix toybox install -m format and C99 str_create(void) declaration
  - Statically linked (LDFLAGS+=-static in Makefile)
  - R32: settings.os validated for Linux/OHOS
  - R33: Compiler from Conan conf, not shell env vars
  - R38: Command-line tool — commands.json declared at software level
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ScdocConan(ConanFile):
    name = "scdoc"
    version = "1.11.0"
    description = "Simple man page composer using a custom markup language"
    license = "MIT"
    homepage = "https://git.sr.ht/~sircmpwn/scdoc"
    url = "https://git.sr.ht/~sircmpwn/scdoc"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32: Use "in" for settings.os check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"scdoc supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not from undefined shell env vars.
        # The profile registers tools.build:compiler_executables as a *dict*
        # ({c, cpp}); the `:c` sub-key form is NOT a registered conf.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # scdoc Makefile uses $(CC), so passing CC= on command line overrides it
        # Must run in source_folder because basic_layout separates build dir
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # Copy the executable binary
        copy(self, "scdoc", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Copy man pages
        copy(self, "scdoc.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "scdoc.5", self.source_folder, os.path.join(self.package_folder, "share", "man", "man5"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
