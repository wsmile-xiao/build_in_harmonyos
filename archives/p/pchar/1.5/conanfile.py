#!/usr/bin/env python3
"""Conan recipe for pchar 1.5 (Autotools).

pchar ("Path Char") is a network path characterization tool produced by
Sandia National Laboratories: it probes a destination host with ICMP,
UDP or TCP packets and reports RTT, jitter and loss statistics.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
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
        copy(
            self,
            "replay_ipv4.txt",
            src=os.path.join(self.recipe_folder, "test_package", "fixtures"),
            dst=os.path.join(self.export_sources_folder, "test_data"),
        )

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"OHOS builds require armv8, got {self.settings.arch}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        copy(
            self,
            "replay_ipv4.txt",
            src=os.path.join(self.export_sources_folder, "test_data"),
            dst=self.source_folder,
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

        output = os.path.join(self.source_folder, "replay-output.txt")
        self.run(
            f'PATH="{self.build_folder}:$PATH" pchar -r replay_ipv4.txt -n > "{output}"',
            cwd=self.source_folder,
        )
        with open(output, encoding="utf-8") as result:
            output_text = result.read()
        if "Path length:" not in output_text or "1 hops" not in output_text:
            raise RuntimeError("pchar replay analysis assertion failed")

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

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
