#!/usr/bin/env python3
"""Conan recipe — pixd 1.0.0

Colourful visualization tool for binary files ("colourful hexdump").
pixd renders each octet as a coloured block using 24-bit SGR escape
sequences; it is a pure-C, single-file CLI (pixd.c) with no external
three-party dependencies beyond the standard C library.

Build system: plain Makefile (implicit rule `pixd: pixd.c`), no configure.
License: MIT
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PixdConan(ConanFile):
    name = "pixd"
    version = "1.0.0"
    description = "Colourful visualization tool for binary files (24-bit SGR hexdump)"
    license = "MIT"
    homepage = "https://github.com/FireyFly/pixd"
    url = "https://github.com/FireyFly/pixd"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # pixd only needs the standard C library shipped with the OHOS
        # toolchain (aarch64-unknown-linux-ohos) — no requires.
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # R9: always -j1 for old single-file make projects.
        # Build only the `pixd` target (the Makefile `all` target also needs
        # gzip for the man page — avoid that toolchain dependency in CI).
        # `</dev/null`: on-device OHOS toolchain binaries (ohos-sdk clang)
        # are refused execution when launched from the conan/python process
        # tree with a pipe as stdin; detaching stdin makes clang run.
        self.run(f'make -j1 CC="{cc}" pixd < /dev/null', cwd=self.source_folder)

    def package(self):
        # pixd is a command-line tool: install the binary to bin/
        copy(self, "pixd", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        pixd_bin = os.path.join(self.package_folder, "bin", "pixd")
        if os.path.exists(pixd_bin):
            os.chmod(pixd_bin, os.stat(pixd_bin).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
