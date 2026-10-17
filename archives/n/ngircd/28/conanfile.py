#!/usr/bin/env python3
"""Conan recipe for ngircd 28 — lightweight Internet Relay Chat (IRC) daemon.

Autotools daemon adapted for HarmonyOS PC (aarch64-linux-ohos).
Depends on openssl/zlib (conan requires) — AutotoolsDeps injects include/lib
dirs, PkgConfigDeps makes openssl's libssl/libcrypto .pc visible to
configure's PKG_CHECK_MODULES. IDENT (--with-ident) is disabled because
libident is not published to the ohpcd registry (see notes.md).
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class NgircdConan(ConanFile):
    name = "ngircd"
    version = "28"
    description = "ngIRCd 28 - lightweight Internet Relay Chat (IRC) daemon"
    license = "GPL-2.0-or-later"
    homepage = "https://ngircd.barton.de/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.8.1")
        self.requires("zlib/1.3.1.2")
        # NOTE: libident/0.32 is adapted in this repo (archives/l/libident/0.32)
        # but NOT published to the ohpcd registry; conan download returns
        # "system acceleration policy not enabled" (non-standard error) and the
        # L0i gate classifies it as registry_unreachable. IDENT is an optional
        # AUTH protocol, so we fall back to --without-ident (documented in notes.md).

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--with-openssl",
            "--with-zlib",
            "--without-ident",
            "--without-gnutls",
            # config.guess cannot recognize HarmonyOS (uname -s = HarmonyOS);
            # pin the build triplet explicitly to skip the guess probe.
            "--build=aarch64-linux-ohos",
        ])
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Upstream installs ngircd into $(sbindir); Conan convention (and the
        # CI application negative test) expects executables under bin/.
        sbin = os.path.join(self.package_folder, "sbin")
        if os.path.isdir(sbin):
            os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
            for name in os.listdir(sbin):
                os.replace(
                    os.path.join(sbin, name),
                    os.path.join(self.package_folder, "bin", name),
                )
            os.rmdir(sbin)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
