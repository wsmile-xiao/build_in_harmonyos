#!/usr/bin/env python3
"""Conan recipe — proftpd-mod_radius 1.3.9c (ProFTPD RADIUS auth module).

Builds ProFTPD with mod_radius as a shared DSO module (openssl-backed
RADIUS Message-Authenticator verification). The packaged artifact is the
mod_radius.so DSO installed into libexec/.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class ProftpdmodradiusConan(ConanFile):
    name = "proftpd-mod_radius"
    version = "1.3.9c"
    description = "ProFTPD mod_radius — RADIUS authentication and accounting module"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/proftpd/proftpd"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # mod_radius uses OpenSSL for RADIUS Message-Authenticator (HMAC-MD5)
        self.requires("openssl/3.5.6.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-dso")
        tc.configure_args.append("--enable-openssl")
        tc.configure_args.append("--with-shared=mod_radius")
        tc.configure_args.append("--disable-nls")
        # mod_radius is a ProFTPD DSO module (libexec/mod_radius.so): the
        # packaged artifact must be a shared object, so keep shared enabled
        # regardless of the recipe's shared option.
        tc.configure_args.append("--enable-shared")
        tc.configure_args.append("--disable-static")
        # Inject openssl dependency paths so configure/make find the headers
        # and libs (proftpd checks <openssl/opensslv.h> via CPPFLAGS).
        openssl = self.dependencies["openssl"].cpp_info
        inc = openssl.includedirs[0] if openssl.includedirs else ""
        lib = openssl.libdirs[0] if openssl.libdirs else ""
        if inc:
            tc.configure_args.append(f"CPPFLAGS=-I{inc}")
        if lib:
            tc.configure_args.append(f"LDFLAGS=-L{lib}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        # Install the mod_radius DSO module under lib/ (conan library
        # layout); consumers and CI find it via libdir. lib/ is the single
        # artifact location so the CI negative test (which moves lib away)
        # can genuinely verify the test depends on the package.
        src = os.path.join(self.build_folder, "modules", ".libs", "mod_radius.so")
        if not os.path.exists(src):
            src = os.path.join(self.build_folder, "modules", "mod_radius.so")
        if not os.path.exists(src):
            raise ConanException("mod_radius.so not found in build tree")
        copy(self, "mod_radius.so", os.path.dirname(src),
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libs = ["mod_radius"]
