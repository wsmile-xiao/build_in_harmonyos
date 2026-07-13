#!/usr/bin/env python3
"""Conan recipe — libevent 2.1.12 (Autotools).

libevent is NOT a system same-name library (R26), so dynamic linking is OK.
Conan manages the full dependency chain.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibeventConan(ConanFile):
    name = "libevent"
    version = "2.1.12"
    description = "Event notification library with fast non-blocking I/O"
    license = "BSD-3-Clause"
    homepage = "https://libevent.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libevent has no Conan-managed dependencies in this build
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R1: minimal parameters, only --prefix (handled by AutotoolsToolchain)
        # R26: libevent is NOT a system same-name library, dynamic linking is OK
        # Disable openssl: it's an optional dependency (cmd-pkgs system package,
        # PR #1732 not yet merged). When openssl is available, remove this flag
        # and add event_openssl to cpp_info.libs + ssl/crypto to system_libs.
        tc.configure_args.append("--disable-openssl")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E011: umask 077→022 fix is handled by 0003-configure.patch
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["event", "event_extra", "event_pthreads"]
        # When openssl is enabled, uncomment the following:
        # self.cpp_info.libs.append("event_openssl")
        # self.cpp_info.system_libs = ["ssl", "crypto"]
