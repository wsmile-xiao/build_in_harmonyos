#!/usr/bin/env python3
"""Conan recipe — podiff 1.4

podiff compares translatable strings and translations between two PO files
(GNU gettext catalogs) or between two revisions of the same file, and can act
as a git external diff driver (GIT_EXTERNAL_DIFF / gitattributes diff=podiff).

Upstream: https://puszcza.gnu.org.ua/software/podiff/ (Sergey Poznyakoff)
Build system: plain flat Makefile (no configure script), single binary,
zero third-party dependencies (libc only).
License: GPL-3.0-or-later
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class PodiffConan(ConanFile):
    name = "podiff"
    version = "1.4"
    description = "Compare translatable strings and translations between two PO files (gettext catalog diff tool, usable as git diff driver)"
    license = "GPL-3.0-or-later"
    homepage = "https://puszcza.gnu.org.ua/software/podiff/"
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

    def generate(self):
        # R33: CC/CFLAGS/LDFLAGS are produced by the Conan toolchain into the
        # conanbuild environment; nothing is read from bare shell variables.
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Flat upstream Makefile (no configure). The portability patch changes
        # the hard-coded `cc` rules to `$(CC)` with `CC ?= cc` /
        # `CFLAGS ?= -ggdb` defaults, so the toolchain environment
        # (CC=/data/service/hnp/bin/clang, CFLAGS from profile) wins.
        # R9: -j1 for small single-binary make projects.
        self.run("make -j1", env="conanbuild", cwd=self.source_folder)

    def package(self):
        # Command-line tool: install the binary (and its man page) only.
        copy(self, "podiff", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "podiff.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH",
                                      os.path.join(self.package_folder, "bin"))
