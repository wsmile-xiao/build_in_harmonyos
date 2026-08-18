#!/usr/bin/env python3
"""Conan recipe for ucon64 2.2.2 — Universal Console file and backup tool.

ucon64 is a command-line tool for managing console ROM images and backup units.
It uses autotools, links against zlib, and must be statically linked (R26: terminal tool).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class Ucon64Conan(ConanFile):
    name = "ucon64"
    version = "2.2.2"
    description = "uCON64 - the Universal Console file and backup tool"
    license = "GPL-2.0-or-later"
    homepage = "https://ucon64.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ucon64 links against zlib for ZIP/archive support
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Tarball has nested src/ directory — promote to top level
        src_dir = os.path.join(self.source_folder, "src")
        if os.path.isdir(src_dir):
            for item in os.listdir(src_dir):
                shutil.move(os.path.join(src_dir, item),
                            os.path.join(self.source_folder, item))
            os.rmdir(src_dir)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # Add zlib lib path for static linking (ucon64 Makefile hardcodes -lz)
        zlib_info = self.dependencies["zlib"].cpp_info
        for libdir in zlib_info.libdirs:
            tc.extra_ldflags.append(f"-L{libdir}")
        for incdir in zlib_info.includedirs:
            tc.extra_cflags.append(f"-I{incdir}")
        tc.generate()

    def build(self):
        # Apply patches from conandata.yml (config.guess, config.sub, configure, parallel.c)
        apply_conandata_patches(self)
        # Run configure and make in-tree (ucon64 doesn't support out-of-tree builds)
        # Use -j1 to avoid mkfifo jobserver issues on HMDFS
        prefix = self.package_folder.replace("\\", "/")
        self.run(
            f'./configure --prefix={prefix} --disable-parallel',
            cwd=self.source_folder,
            env=["conanbuild", "conanautotoolstoolchain"],
        )
        self.run(
            'make -j1',
            cwd=self.source_folder,
            env=["conanbuild", "conanautotoolstoolchain"],
        )

    def package(self):
        # ucon64's install.sh uses sudo and hardcoded paths, so copy manually
        # Binary is built in-tree (source_folder)
        copy(self, "ucon64", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Terminal tool: no libraries to link against
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
