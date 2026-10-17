#!/usr/bin/env python3
"""Conan recipe — enchive 3.5

Enchive is a compact, standalone cryptographic archive utility. It encrypts
files to yourself (asymmetric, public-key) using ChaCha20, Curve25519, and
HMAC-SHA256 — all implemented from scratch in pure C with no external crypto
dependencies (only libc).

Build system: plain Makefile (no configure). `make` produces the `enchive`
command-line tool; `make install PREFIX=...` installs the binary and man page.

OHOS specifics:
  - The Makefile's install target uses `install` and `gzip` commands. The
    `install` coreutil is absent on OHOS, so package() copies the binary
    directly (matching the accrete pattern).
  - Compiler is taken from Conan conf (R33), never bare shell env vars.
  - The default CFLAGS (-ansi -pedantic) are replaced with -O2 for OHOS clang.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class EnchiveConan(ConanFile):
    name = "enchive"
    version = "3.5"
    description = "Compact, standalone cryptographic archive utility (ChaCha20 + Curve25519 + HMAC-SHA256, pure C)"
    license = "Unlicense"
    homepage = "https://github.com/skeeto/enchive"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
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
        # R9: always -j1 for this small single-directory project
        # enchive's Makefile default CFLAGS (-ansi -pedantic -O3) are GCC-oriented;
        # use -O2 which works cleanly with OHOS clang.
        self.run(f'make -j1 CC="{cc}" CFLAGS="-O2" LDFLAGS=""', cwd=self.source_folder)

    def package(self):
        # The Makefile install target relies on /usr/bin/install (absent on OHOS).
        # enchive is a command-line tool: copy the binary straight into bin/.
        copy(self, "enchive", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        # Copy license
        copy(self, "UNLICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Copy man page (pre-gzipped not needed for package, but include source)
        copy(self, "enchive.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share/man/man1"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
