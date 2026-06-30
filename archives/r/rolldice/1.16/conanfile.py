#!/usr/bin/env python3
"""Conan recipe — rolldice 1.16 (plain Makefile build system).

Builds rolldice, a virtual dice rolling command-line tool.
Uses a plain Makefile (not autotools/configure).
R26: static linking for terminal tools (BUILD_SHARED_LIBS=OFF).
Source modified: readline replaced with getline() for OHOS portability.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class RolldiceConan(ConanFile):
    name = "rolldice"
    version = "1.16"
    description = "Rolls an amount of virtual dice"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/sstrickl/rolldice"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies — readline replaced with getline()
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF)
        env = Environment()
        env.define("BUILD_SHARED_LIBS", "OFF")
        env.append("LDFLAGS", "-static")
        envvars = env.vars(self, scope="build")
        envvars.save_script("rolldice_env")

    def build(self):
        apply_conandata_patches(self)
        # Plain Makefile build — no configure step needed
        # -j1: HarmonyOS jobserver mkfifo not permitted (E046)
        # -C: run make in source folder (basic_layout separates source/build dirs)
        self.run(f"make -j1 -C {self.source_folder}")

    def package(self):
        # Install binary and man page (artifacts are in source folder)
        copy(self, "rolldice", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        man_src = os.path.join(self.source_folder, "rolldice.6")
        if os.path.exists(man_src):
            copy(self, "rolldice.6", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man6"))

    def package_info(self):
        # Terminal tool — cpp_info.libs must be set (R26)
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
