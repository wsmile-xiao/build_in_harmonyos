#!/usr/bin/env python3
"""Conan recipe — pgdbf 0.6.2 (autotools CLI tool).

pgdbf converts XBase / dBase / FoxPro .dbf files into SQL suitable for
PostgreSQL import.  Upstream ships a 2012 autotools tree:

1. Its bundled config.guess cannot recognise the HarmonyOS kernel
   (``uname -s = HarmonyOS`` -> "cannot guess build type"), so the
   aarch64-linux triplet is passed explicitly -- same pattern as
   archives/a/a52dec (which also carries a config.sub patch); pgdbf's
   config.sub already knows ``aarch64-unknown-linux-gnu``.
2. configure/config.status create their private ./confXXXXXX temp dir
   with ``(umask 077 && mktemp -d)``.  On hmdfs the setgid parent turns
   that into an unwritable ``drwx--S---`` directory and configure dies
   with "Permission denied"/"could not setup config files machinery"
   (knowledge: abnfgen E-record).  We relax umask 077 -> 022 before
   running configure; ssmtp/abnfgen apply the same class of fix.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (get, apply_conandata_patches,
                               export_conandata_patches, load, save)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PgdbfConan(ConanFile):
    name = "pgdbf"
    version = "0.6.2"
    description = "Convert XBase / dBase / FoxPro DBF files into PostgreSQL import format"
    license = "GPL-3.0-or-later"
    homepage = "http://pgdbf.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pgdbf supports Linux/OHOS only, got {self.settings.os}"
            )
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                "pgdbf is packaged for the aarch64 target"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess (2012) cannot detect `uname -s=HarmonyOS`
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

    def _patch_configure_umask(self, configure_path):
        """Relax umask 077 -> 022 in configure's temp-dir handling."""
        contents = load(self, configure_path)
        if "umask 077" not in contents:
            return
        contents = contents.replace("umask 077", "umask 022")
        save(self, configure_path, contents)

    def build(self):
        apply_conandata_patches(self)
        configure_path = os.path.join(self.source_folder, "configure")
        self._patch_configure_umask(configure_path)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
