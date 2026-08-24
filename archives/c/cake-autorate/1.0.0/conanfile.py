#!/usr/bin/env python3
"""Conan recipe — cake-autorate 1.0.0 (OpenWrt CAKE QoS adaptive rate).

cake-autorate is a shell script that minimizes latency by adjusting
CAKE bandwidth settings based on traffic load and round-trip time
measurements. Designed for variable bandwidth connections (LTE,
Starlink, cable modems).

Pure shell script package — no compilation. Install layout:
  bin/cake-autorate.sh          — main monitoring/adjustment script
  bin/cake-autorate-setup.sh    — installation helper
  bin/cake-autorate-config.sh   — configuration editor
  bin/cake-autorate             — OpenWrt init.d wrapper
  share/cake-autorate/LICENCE.md
  share/cake-autorate/Example_Starlink_config.sh

Run-time deps: bash, fping, tc (iproute2).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get
from conan.tools.layout import basic_layout


class CakeAutorateConan(ConanFile):
    name = "cake-autorate"
    version = "1.0.0"
    description = "Adaptive CAKE bandwidth shaping for variable-rate links"
    license = "MIT"
    homepage = "https://github.com/lynxthecat/cake-autorate"
    url = "https://github.com/lynxthecat/cake-autorate"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Pure shell script package — nothing to compile.
        # Ensure scripts are executable.
        scripts = [
            "cake-autorate.sh",
            "cake-autorate-setup.sh",
            "cake-autorate-config.sh",
            "cake-autorate",
        ]
        for s in scripts:
            p = os.path.join(self.source_folder, s)
            if os.path.isfile(p):
                os.chmod(p, 0o755)

    def package(self):
        # Install main scripts to bin/
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)

        scripts = [
            "cake-autorate.sh",
            "cake-autorate-setup.sh",
            "cake-autorate-config.sh",
            "cake-autorate",
        ]
        for s in scripts:
            src = os.path.join(self.source_folder, s)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(bin_dir, s))
                os.chmod(os.path.join(bin_dir, s), 0o755)

        # Install example config + license to share/cake-autorate/
        share_dir = os.path.join(
            self.package_folder, "share", "cake-autorate"
        )
        os.makedirs(share_dir, exist_ok=True)
        for f in ["LICENCE.md", "Example_Starlink_config.sh",
                  "CHANGELOG.md", "README.md"]:
            src = os.path.join(self.source_folder, f)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(share_dir, f))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            self.buildenv_info.append_path("PATH", bin_dir)
