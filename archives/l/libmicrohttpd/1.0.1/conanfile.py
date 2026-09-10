#!/usr/bin/env python3
"""Conan recipe for GNU libmicrohttpd 1.0.1 (autotools)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmicrohttpdConan(ConanFile):
    name = "libmicrohttpd"
    version = "1.0.1"
    description = "GNU libmicrohttpd: embeddable HTTP server library for C"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gnu.org/software/libmicrohttpd/"
    url = "https://ftp.gnu.org/gnu/libmicrohttpd/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # No texinfo in build env: skip docs. Optional HTTPS (gnutls) kept off.
        tc.configure_args.append("--disable-doc")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j4"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["microhttpd"]