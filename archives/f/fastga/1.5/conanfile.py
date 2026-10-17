#!/usr/bin/env python3
"""Conan recipe for FASTGA 1.5 — plain Makefile command-line suite."""
import os
import shlex

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class FastgaConan(ConanFile):
    name = "fastga"
    version = "1.5"
    description = "Fast genome aligner and genome database utility suite"
    license = "BSD-3-Clause AND MIT"
    homepage = "https://github.com/thegenemyers/FASTGA"
    url = "https://github.com/thegenemyers/FASTGA"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _executables = (
        "FAtoGDB", "GDBtoFA", "GDBstat", "GDBshow", "GIXmake", "GIXshow",
        "GIXrm", "GIXmv", "GIXcp", "FastGA", "ALNshow", "ALNtoPAF",
        "ALNtoPSL", "ALNreset", "ALNplot", "ALNchain", "PAFtoALN",
        "PAFtoPSL", "ONEview", "FastKS", "ONEalnTEST", "ANOstat",
        "ANOshow", "ANOtoBED", "BEDtoANO",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: derive compiler and baseline flags from Conan's generated toolchain.
        toolchain_vars = AutotoolsToolchain(self).vars()
        cc = toolchain_vars.get("CC", "clang")
        cflags = toolchain_vars.get("CFLAGS", "-O3")
        zlib_root = self.dependencies["zlib"].package_folder
        flags = "{} -Wall -Wextra -Wno-unused-result -fno-strict-aliasing -I{} -L{}".format(
            cflags,
            os.path.join(zlib_root, "include"),
            os.path.join(zlib_root, "lib"),
        )
        self.run(
            "make -j1 CC={} CFLAGS={}".format(shlex.quote(cc), shlex.quote(flags)),
            cwd=self.source_folder,
        )
        # Upstream v1.5 provides no check/test target; test_package exercises FAtoGDB.

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for executable in self._executables:
            copy(self, executable, self.source_folder, bindir, keep_path=False)
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
