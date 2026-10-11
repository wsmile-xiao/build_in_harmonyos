#!/usr/bin/env python3
"""Conan recipe for pimd 2.3.2 - PIM-SM multicast routing daemon.

pimd ships a hand-written ``configure`` script that generates ``config.mk``,
which the top-level Makefile includes.  There are no third-party dependencies:
on Linux/HarmonyOS the recipe builds the bundled libite objects it needs
(strlcpy, strlcat, pidfile, strtonum) directly.

The source is the Debian orig tarball (the upstream project publishes release
tarballs only; the bundled libite submodule is present in the Debian tarball),
byte-pinned by sha256.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout


class PimdConan(ConanFile):
    name = "pimd"
    version = "2.3.2"
    description = "PIM-SM multicast routing daemon (protocol independent multicast)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/troglobit/pimd"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pimd OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        self.run("sh ./configure", cwd=self.source_folder)
        self.run('make CC="{}" -j1'.format(cc), cwd=self.source_folder)
        if not os.path.isfile(os.path.join(self.source_folder, "pimd")):
            raise ConanInvalidConfiguration("build did not produce the 'pimd' program")

    def package(self):
        copy(self, "pimd", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "pimd.8", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "pimd.conf", self.source_folder,
             os.path.join(self.package_folder, "share", "pimd"))
        copy(self, "LICENSE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "AUTHORS", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
