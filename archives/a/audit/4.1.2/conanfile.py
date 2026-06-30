#!/usr/bin/env python3
"""Conan recipe — audit 4.1.2 (Linux Audit System userspace).

Build system: autotools
Source: https://github.com/linux-audit/audit-userspace/archive/refs/tags/v4.1.2.tar.gz

Rules compliance:
  R1:  Minimal configure args (--prefix handled by AutotoolsToolchain)
  R26: System same-name libs (libaudit, libauparse) built static via --disable-shared
  R27: No external dependencies (requirements() is empty)
  R32: settings.os validated with in ("Linux", "OHOS")
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AuditConan(ConanFile):
    name = "audit"
    version = "4.1.2"
    description = "Userspace tools and libraries for the Linux Audit System"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/linux-audit/audit-userspace"
    url = ""  # CI fills this

    # R26: audit produces system same-name libraries (libaudit, libauparse)
    # Build static to avoid polluting /lib, /lib64
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: No external dependencies — requirements() is empty
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os must be checked with in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"audit 4.1.2 only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System same-name libraries (libaudit, libauparse) must be static
        # --disable-shared prevents .so output that could pollute /lib, /lib64
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-zos-remote")
        tc.configure_args.append("--without-python3")
        # R8: Define __OHOS__ so #ifdef __OHOS__ guards in patches are active
        tc.extra_defines.append("__OHOS__")
        tc.generate()

    def build(self):
        # GitHub tarball does not contain pre-generated autotools files.
        # Patches 0006/0007 add OHOS-aware config.guess/config.sub as new files.
        # Strategy: apply patches first, save config.guess/config.sub,
        # then autoreconf -fi (which overwrites them but installs other aux files),
        # then restore the OHOS versions.
        # OHOS: umask 000 needed for config.status temp dir creation
        os.umask(0)
        apply_conandata_patches(self)
        # Save OHOS-patched config.guess/config.sub before autoreconf overwrites them
        self.run("cp config.guess config.guess.ohos", cwd=self.source_folder)
        self.run("cp config.sub config.sub.ohos", cwd=self.source_folder)
        # autoreconf -fi: generates configure, Makefile.in, installs aux files
        self.run("umask 000 && autoreconf -fi", cwd=self.source_folder)
        # Restore OHOS-patched config.guess/config.sub
        self.run("mv -f config.guess.ohos config.guess", cwd=self.source_folder)
        self.run("mv -f config.sub.ohos config.sub", cwd=self.source_folder)
        # OHOS: Patch configure to use umask 000 for config.status temp dirs
        # Autoconf generates "umask 077" for temp dir creation which fails on OHOS
        self.run("sed -i 's/umask 077/umask 000/g' configure", cwd=self.source_folder)
        # Use Autotools.configure() which sources Conan environment files
        # (CFLAGS with -D__OHOS__, etc.) — critical for lib/ Makefile
        autotools = Autotools(self)
        autotools.configure()
        # OHOS: Run make with -j1 to avoid jobserver mkfifo (not supported on OHOS)
        # CPPFLAGS: -D__OHOS__ activates #ifdef guards in patches
        #           -D_UAPI_LINUX_SOCKET_H prevents linux/socket.h (conflicts with sys/socket.h)
        #           -include sys/socket.h ensures socket structs available before linux/net.h
        # Use self.run() instead of autotools.make() for proper shell quoting
        self.run('make -j1 CPPFLAGS="-D__OHOS__ -D_UAPI_LINUX_SOCKET_H -include sys/socket.h"')

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["audit", "auparse"]
        self.cpp_info.includedirs = ["include"]
