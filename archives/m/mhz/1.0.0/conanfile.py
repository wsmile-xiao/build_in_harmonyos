#!/usr/bin/env python3
"""Conan recipe for mhz 1.0.0 - measure the CPU's effective frequency.

Upstream is a single C file with a hand-written Makefile and no third-party
dependencies.  The program runs a pair of dependent-instruction loops and uses
CLOCK_MONOTONIC to derive the CPU frequency in MHz (rdtsc is only used when the
target is x86, so on aarch64 it simply reports the measured CPU clock).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout


class MhzConan(ConanFile):
    name = "mhz"
    version = "1.0.0"
    description = "Measure the CPU's effective frequency (MHz)"
    license = "MIT"
    homepage = "https://github.com/wtarreau/mhz"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mhz OHOS adaptation is validated on Linux/OHOS, not "
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
        self.run('make CC="{}" -j1'.format(cc), cwd=self.source_folder)
        if not os.path.isfile(os.path.join(self.source_folder, "mhz")):
            raise ConanInvalidConfiguration("build did not produce the 'mhz' program")

    def package(self):
        copy(self, "mhz", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README*", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
