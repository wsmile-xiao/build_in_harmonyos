#!/usr/bin/env python3
"""Conan recipe for mp3wrap 0.5 — a command-line utility that wraps two or
more MP3 files into a single large playable MP3 file without losing
filename and ID3 information.

Upstream: http://mp3wrap.sourceforge.net/
License:  LGPL-2.0-or-later (source COPYING = GNU Library GPL v2)
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Mp3wrapConan(ConanFile):
    name = "mp3wrap"
    version = "0.5"
    description = "Command-line utility to wrap multiple MP3 files into one large playable MP3 file"
    license = "LGPL-2.0-or-later"
    homepage = "https://mp3wrap.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mp3wrap supports Linux and OHOS, not {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                f"OHOS builds require armv8/aarch64, not {self.settings.arch}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # mp3wrap 0.5 ships an ancient automake-1.5 configure with no
            # bundled config.sub / config.guess.  Cross-compilation triple
            # hints are harmless here (configure only probes CC/INSTALL) but
            # pass them so the build/host alias logic does not break.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # mp3wrap 0.5 tarball ships a stale config.status (a 2003-era
        # distribution artifact), which triggers configure's
        # "source directory already configured" guard.  Remove it
        # and config.log before configuring so the build is clean.
        for stale in ("config.status", "config.log", "config.cache"):
            stale_path = os.path.join(self.source_folder, stale)
            if os.path.exists(stale_path):
                os.remove(stale_path)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream has NO test suite — make check just rebuilds.
        # (Makefile.in: check-am: all-am / check: check-am)
        # We still run it to confirm the target is a no-op.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
