#!/usr/bin/env python3
"""Conan recipe — sluice 0.03.01 (rate limiting data piping tool).

Upstream: https://github.com/ColinIanKing/sluice
Reads standard input and writes it to standard output at a specified data
rate (I/O streaming benchmarking / throughput exercising).

Build system: plain Makefile (no configure step). Single C translation unit
(sluice.c) compiled into one executable `sluice`. Upstream CI (.travis.yml)
runs `make -j2 PEDANTIC=$PEDANTIC` — a compile gate only.

No third-party dependencies: pure C against libc (fcntl F_SETPIPE_SZ,
sysconf, sigaction — all available on OHOS musl; verified on device).

License: GPL-2.0-or-later (upstream COPYING).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SluiceConan(ConanFile):
    name = "sluice"
    version = "0.03.01"
    description = "sluice — rate limiting data piping tool: forwards stdin to stdout at a specified data rate"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ColinIanKing/sluice"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # no third-party dependencies (pure C, libc only)

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
        # R33: compiler must come from Conan conf, never from bare shell env
        # vars (release workers have them unset).
        # NOTE: do NOT pass CFLAGS on the make command line — a command-line
        # variable overrides the Makefile's own `CFLAGS += -Wall -Wextra
        # -DVERSION='"$(VERSION)"' -O2` (+= is ignored for command-line
        # vars), which would drop -DVERSION and fail the build with
        # "use of undeclared identifier 'VERSION'".  The upstream CFLAGS
        # defaults are self-contained, so only CC is injected.
        # R9: single -j1 for this small plain-Makefile project.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        self.run(
            f'make -j1 CC="{cc}"',
            cwd=self.source_folder,
        )

    def package(self):
        # sluice is a command-line tool: install the binary to bin/
        copy(self, "sluice", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
