#!/usr/bin/env python3
"""Conan recipe — pidof 2.86 (Makefile).

pidof is a simple standalone CLI tool that reads /proc to find the process
IDs of running programs. This is a stripped-down version from the sysvinit
suite, keeping only the pidof functionality (no killall5).

Upstream ships a minimal Makefile with no configure, no autotools, and no
install target that respects DESTDIR by default. The Makefile hardcodes
`cp $(APP) $(DESTDIR)/usr/bin` in its install target, so build() overrides
CC/CFLAGS/LDFLAGS from the Conan toolchain (R33) and package() installs
the binary by hand.

OHOS notes:
  - libc (musl) already contains all required routines. No external deps.
  - pidof reads /proc directly — no glibc-specific APIs are used.
  - No patches needed: the source is pure POSIX and compiles cleanly.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PidofConan(ConanFile):
    name = "pidof"
    version = "2.86"
    description = "Find the process ID of a running program (standalone, from sysvinit)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/drmrboy/pidof"
    url = "https://github.com/drmrboy/pidof"
    topics = ("pidof", "process", "sysvinit")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pidof supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_c(self):
        # R33: take the compiler from the Conan profile, never from ${CC}.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or "clang"

    def build(self):
        cc = self._compiler_c()
        # pidof reads /proc — needs _GNU_SOURCE for some glibc/musl compat.
        # -fPIE/-pie/relro/now harden the binary.
        cflags = "-O2 -fPIE -D_GNU_SOURCE"
        ldflags = "-pie -Wl,-z,relro,-z,now"
        self.run(
            f'make CC="{cc}" CFLAGS="{cflags}" LDFLAGS="{ldflags}" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "pidof", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Upstream ships no LICENSE file; GPL-2.0-only notice is in pidof.c header.
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        os.chmod(os.path.join(self.package_folder, "bin", "pidof"), 0o755)

    def package_info(self):
        self.cpp_info.libs = []  # pidof is a CLI tool, it ships no library
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
