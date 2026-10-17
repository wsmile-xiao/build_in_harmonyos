#!/usr/bin/env python3
"""Conan recipe for cmdpack 1.06."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class CmdpackConan(ConanFile):
    name = "cmdpack"
    version = "1.06"
    description = "Command-line tools for binary files, CD images, patches, audio data, and ROM analysis"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/chungy/cmdpack"
    url = "https://github.com/chungy/cmdpack"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _programs = (
        "bin2ecm",
        "bincomp",
        "brrrip",
        "byteshuf",
        "cdpatch",
        "fakecrc",
        "hax65816",
        "pecompat",
        "rels",
        "screamf",
        "uips",
        "vb2rip",
        "wordadd",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        if not cc and cross_building(self):
            raise ConanInvalidConfiguration(
                "cross-building cmdpack requires "
                "tools.build:compiler_executables['c']"
            )
        cc = cc or "clang"
        self.run(f'make -C "{self.source_folder}" clean')
        self.run(
            f'make -C "{self.source_folder}" CC="{cc}" VERSION=v{self.version} -j1'
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        for program in self._programs:
            copy(self, program, src=self.source_folder, dst=bin_dir, keep_path=False)

        # bin2ecm switches to decode mode from argv[0]. A real copy is more
        # reliable than an install-time symlink on HarmonyOS/HMDFS.
        source = os.path.join(bin_dir, "bin2ecm")
        destination = os.path.join(bin_dir, "ecm2bin")
        if os.path.isfile(source):
            shutil.copy2(source, destination)

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "README.adoc",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "res"),
            keep_path=False,
        )
        copy(
            self,
            "*.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "res", "man"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
