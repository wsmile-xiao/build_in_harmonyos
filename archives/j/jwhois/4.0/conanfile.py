#!/usr/bin/env python3
"""Conan recipe — jwhois 4.0

GNU improved whois client: queries WHOIS servers, follows referral chains.
Build system: Autotools (release tarball ships configure, no autoreconf needed).
License: GPL-3.0-or-later (source headers: "either version 3 of the License").
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JwhoisConan(ConanFile):
    name = "jwhois"
    version = "4.0"
    description = "GNU improved whois client - queries WHOIS servers and follows referral chains"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/jwhois/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 2007-era config.guess/sub can't guess on OHOS (HMDFS denies the dummy
        # compile) and don't know "ohos" triplets: force build triplet (adms style)
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # gettext/NLS off: no msgfmt/libintl on OHOS musl; client is English-only
        tc.configure_args.append("--disable-nls")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E011: HMDFS + umask 077 in shipped configure breaks config.status
        # temp files (Permission denied on conf*/*) - normalize to 022 (gsl-style)
        import glob
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            with open(_cfg, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
