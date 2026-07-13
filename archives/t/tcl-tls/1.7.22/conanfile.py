#!/usr/bin/env python3
"""Conan recipe — tcl-tls 1.7.22 (Tcl TLS/SSL extension).

tcl-tls provides TLS/SSL support for Tcl via OpenSSL.
It is a shared library (.so) loaded by Tcl's `package require tls`.

Dependencies: tcl (Conan package tcl/9.0.3.1), openssl (Conan package openssl/3.5.6)
Build system: autotools (configure + make)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TcltlsConan(ConanFile):
    name = "tcl-tls"
    version = "1.7.22"
    description = "Tcl TLS/SSL extension providing SSL/TLS support for Tcl"
    license = "MIT"
    homepage = "https://core.tcl-lang.org/tcltls"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("tcl/9.0.3.1")
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Tcl 9.0 compatibility macros (tcl-tls 1.7.22 was written for Tcl 8.x)
        tc.extra_cflags.extend([
            "-DCONST=const",
            "-DVOID=void",
            "-D_ANSI_ARGS_\\(x\\)=x",
            "-DTCL_CHANNEL_VERSION_2=TCL_CHANNEL_VERSION_5",
        ])
        # Point to Conan-resolved tcl installation
        tcl_pkg = self.dependencies["tcl"].package_folder
        tc.configure_args.append(f"--with-tcl={tcl_pkg}/lib")

        # Use Conan's OpenSSL package (provides headers + static libs)
        openssl_pkg = self.dependencies["openssl"].package_folder
        tc.configure_args.append(f"--with-openssl-dir={openssl_pkg}")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix pkgIndex.tcl for Tcl 9 compatibility (8.5 -> 8.5-)
        pkgindex = os.path.join(self.source_folder, "pkgIndex.tcl")
        if os.path.exists(pkgindex):
            replace_in_file(self, pkgindex, "8.5", "8.5-")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # objcopy commands in Makefile are prefixed with - so errors are ignored
        # On OHOS, objcopy-processed .so files can't be dlopen'd (Permission denied)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["tcltls"]
        self.cpp_info.libdirs = ["lib/tcltls1.7.22"]
