#!/usr/bin/env python3
"""Conan recipe for cfm (Cactus File Manager) 0.6.6.

cfm is a single-file C TUI file manager with no external dependencies
(beyond libc/POSIX). Build system: plain Makefile (no configure).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class CfmConan(ConanFile):
    name = "cfm"
    version = "0.6.6"
    description = "Cactus File Manager - simple and fast TUI file manager with no dependencies"
    license = "MPL-2.0"
    homepage = "https://github.com/sophec/cfm"
    url = "https://github.com/sophec/cfm"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # R33: GnuToolchain injects CC/CFLAGS from the Conan profile (no shell env vars)
    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The Makefile generates config.h from config.def.h on demand.
        with chdir(self, self.source_folder):
            # R9: Always use -j1
            self.run("make -j1")

    def package(self):
        # NOTE: upstream `make install` needs the GNU `install` command which is
        # not available on HarmonyOS (knowledge E108/E182); copy artifacts directly.
        copy(self, "cfm", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "cfm.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
