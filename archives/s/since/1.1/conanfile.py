#!/usr/bin/env python3
"""Conan recipe for since — tail(1) with state.

since prints only the lines that were appended to a file since the last
time it was run, keeping its bookkeeping in a per-user state file.

Key adaptation points for HarmonyOS PC (aarch64):
  - Upstream Makefile hard-codes `CC = gcc` and overwrites CFLAGS, which
    breaks cross compilation; patched to honour external CC/CFLAGS/CPPFLAGS/
    LDFLAGS (patches/0001-Makefile.patch).
  - The inotify probe in the Makefile tested the *build host* header
    (/usr/include/sys/inotify.h); patched to probe with the target compiler
    so the feature is decided by the OHOS sysroot.
  - CC comes from Conan conf (R33: never rely on bare shell env vars).
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class SinceConan(ConanFile):
    name = "since"
    version = "1.1"
    description = "since — tail(1) with state: show only lines appended since the last run"
    license = "GPL-3.0-or-later"
    homepage = "http://welz.org.za/projects/since"
    url = "https://salsa.debian.org/debian/since"
    topics = ("log", "tail", "cli", "monitoring")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        # AutotoolsToolchain is used only for its environment (CFLAGS/CPPFLAGS/
        # LDFLAGS/CC): the project is a plain Makefile with no configure script.
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler comes from Conan conf, never from a bare shell variable.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        self.run(f'make CC="{cc}" -j1', cwd=self.source_folder)

    def package(self):
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "since", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "since.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
