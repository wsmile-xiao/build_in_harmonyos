#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Ell, ell, 0.71, ell 0.71, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class EllConan(ConanFile):
    name = "ell"
    version = "0.71"
    description = "ell 0.71"
    license = "LGPL-2.1-or-later"
    homepage = "https://git.kernel.org/pub/scm/libs/ell/ell.git"
    url = "https://kernel.org/pub/linux/libs/ell/ell-0.71.tar.xz"

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
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # --enable-maintainer-mode: upstream gates the openssl/xxd detection
        # (and therefore cert_tests + examples) behind USE_MAINTAINER_MODE,
        # so without it only 43 of the 46 registered TESTS get built.
        tc.configure_args.append("--enable-maintainer-mode")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ell"]
