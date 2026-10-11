#!/usr/bin/env python3
"""Conan recipe for pchar 1.5 (Autotools).

pchar ("Path Char") is a network path characterization tool produced by
Sandia National Laboratories: it probes a destination host with ICMP,
UDP or TCP packets and reports RTT, jitter and loss statistics.
"""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PcharConan(ConanFile):
    name = "pchar"
    version = "1.5"
    description = "Network path characterization tool (ICMP/UDP/TCP RTT/jitter/loss analysis)"
    license = "public-domain"
    homepage = "https://www.kitchenlab.org/www/bmah/Software/pchar/"
    url = ""  # CI fills this
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Upstream ships no separate license file; the README carries the
        # Sandia/DOE public dedication text.
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
