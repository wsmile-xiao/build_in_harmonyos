#!/usr/bin/env python3
"""Conan recipe — rio 1.07

rio is the command line utility of The Snowblind Alliance for the Diamond
Rio PMP300 portable MP3 player.  It drives the player over the PC parallel
port and manages its flash memory: directory listing, upload, download,
delete, initialise and playlist ordering.

Build system: plain Makefile (`$(CXX) $(CXXFLAGS) -o rio app.cpp rio.cpp`),
no configure script and no test suite.

HarmonyOS PC (aarch64) adaptation:
  * LP64 data model — SIGNED32/UNSIGNED32 must stay exactly 32 bit wide,
    otherwise the serialised directory structures (512/128/16 bytes) and the
    block checksums are corrupted;
  * the OHOS libc is musl based: <sys/perm.h> and <asm/io.h> do not exist,
    and sys_errlist[] has been removed (strerror() is used instead);
  * aarch64 has no ISA I/O port space, so the port registers are accessed
    through the portable byte-stream interface of /dev/port.

License: GPL-2.0-only (see gpl.txt inside the source archive).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RioConan(ConanFile):
    name = "rio"
    version = "1.07"
    description = "Command line utility for the Diamond Rio PMP300 portable MP3 player (parallel port protocol)"
    license = "GPL-2.0-only"
    homepage = "https://packages.debian.org/source/rio"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # rio only needs the C/C++ runtime library.
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

        # R33: take the compiler from the Conan toolchain, never from bare
        # shell environment variables (they are empty on the CI workers).
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = comp_execs.get("cpp") or comp_execs.get("cxx") or "clang++"

        # R9: two translation units and an old fashioned makefile -> -j1.
        # CXXFLAGS keeps the upstream default (-O1) declared in the makefile.
        self.run(f'make -j1 CXX="{cxx}"', cwd=self.source_folder)

    def package(self):
        # rio is a command line tool: install the binary into bin/
        copy(self, "rio", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command line tool, not a library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
