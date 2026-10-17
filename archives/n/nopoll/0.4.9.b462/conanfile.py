#!/usr/bin/env python3
"""Conan recipe — nopoll 0.4.9.b462 (autotools).

noPoll: WebSocket toolkit (C library) by ASPL.
Builds libnopoll static library and nopoll headers.
TLS support provided by openssl (conan-managed).

Upstream: https://www.aspl.es/nopoll (GitHub: ASPLes/nopoll)
Version 0.4.9.b462 is the official release tarball from aspl.es
(GitHub tag is 0.4.9; VERSION file inside the tarball is 0.4.9.b462).
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class NopollConan(ConanFile):
    name = "nopoll"
    version = "0.4.9.b462"
    description = "noPoll — WebSocket toolkit (C library, no dependencies beyond OpenSSL)"
    license = "LGPL-2.1"
    homepage = "https://www.aspl.es/nopoll"
    url = "https://github.com/ASPLes/nopoll"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # disable debug log support for release builds (upstream option, default yes)
        tc.configure_args.append("--disable-nopoll-log")
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        # Patches applied from conandata.yml:
        #  0001 config.guess  — HarmonyOS triplet detection (E205)
        #  0002 config.sub    — aarch64-unknown-linux-ohos support (E205/E072)
        #  0003 configure     — umask 077 -> TMPDIR redirect (E129, HMDFS)
        #  0004 Makefile(.am/.in) — tolerate missing .libs/libnopoll.exp on
        #      static-only builds (upstream update-def only works for DLLs)
        #  0005 nopoll_conn.c — set accepted sockets non-blocking (upstream
        #      issue #56), prevents listener loop stall
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # remove libtool archives with hardcoded absolute libdir
        for _la in glob.glob(os.path.join(self.package_folder, "**", "*.la"), recursive=True):
            try:
                os.remove(_la)
            except OSError:
                pass

    def package_info(self):
        self.cpp_info.libs = ["nopoll"]
        self.cpp_info.set_property("cmake_file_name", "nopoll")
        self.cpp_info.set_property("cmake_target_name", "nopoll::nopoll")
        self.cpp_info.set_property("pkg_config_name", "nopoll")
        self.cpp_info.system_libs = ["pthread"]
