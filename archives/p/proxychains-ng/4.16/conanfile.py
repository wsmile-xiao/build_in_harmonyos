#!/usr/bin/env python3
"""Conan recipe — proxychains-ng 4.16 (proxychains new generation).

Build system: autotools (custom configure script, not autoconf)
Source: https://github.com/rofl0r/proxychains-ng/archive/refs/tags/v4.16.tar.gz

Rules compliance:
  R1:  Minimal configure args (--prefix only)
  R26: Not a system same-name library, no static enforcement needed
  R27: No external dependencies (requirements() is empty)
  R32: settings.os validated with in ("Linux", "OHOS")
  R33: No shell env vars in build(); compiler flags from Conan toolchain
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class ProxychainsNgConan(ConanFile):
    name = "proxychains-ng"
    version = "4.16"
    description = "proxychains-ng - forces any TCP connection through a proxy (SOCKS4/SOCKS5/HTTP)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/rofl0r/proxychains-ng"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # proxychains-ng produces both a tool (proxychains4) and a shared library
    # (libproxychains4.so). Set as shared-library so cpp_info.libs is exported
    # to CMakeDeps for consumer linking.
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies — only needs libc
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os must be checked with in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"proxychains-ng 4.16 only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # proxychains-ng uses a custom configure script (not autoconf).
        # It does NOT support --enable-static / --disable-shared flags.
        # The library (libproxychains4.so) is always built shared — it is
        # loaded via LD_PRELOAD, so static linking is not applicable.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # proxychains-ng uses a custom configure script (not autoconf).
        # The configure generates config.mak (included by the pre-existing
        # Makefile). Both configure and make must run from the source
        # directory where the Makefile lives.
        # Use --prefix=/ so that DESTDIR in package() maps correctly.
        self.run("./configure --prefix=/", cwd=self.source_folder)
        # OHOS: -j1 to avoid jobserver mkfifo (not supported on OHOS)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install binaries, library, and config files using DESTDIR
        # to install into the Conan package folder.
        destdir = self.package_folder
        self.run(f'make install DESTDIR="{destdir}"', cwd=self.source_folder)
        # proxychains-ng has a separate install-config target for config files
        self.run(f'make install-config DESTDIR="{destdir}"', cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["proxychains4"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        # Config file directory (etc/proxychains.conf)
        self.cpp_info.resdirs = ["etc"]
