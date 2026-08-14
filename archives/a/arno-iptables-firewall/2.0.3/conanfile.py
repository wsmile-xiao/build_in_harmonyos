#!/usr/bin/env python3
"""Conan recipe for arno-iptables-firewall 2.0.3.

Arno's iptables firewall is a single- & multi-homed firewall script
with DSL/ADSL support. It is a pure shell-script tool — no compilation
needed. This recipe packages the scripts and configuration files.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class ArnoIptablesFirewallConan(ConanFile):
    name = "arno-iptables-firewall"
    version = "2.0.3"
    description = "Single- & multi-homed firewall script with DSL/ADSL support"
    license = "GPL-2.0-or-later"
    homepage = "https://rocky.eld.leidenuniv.nl/"
    url = "https://github.com/arno-iptables-firewall/aif"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # Main firewall script -> sbin/
        copy(self, "arno-iptables-firewall",
             src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "sbin"))
        os.chmod(
            os.path.join(self.package_folder, "sbin", "arno-iptables-firewall"),
            0o755,
        )

        # Log filter script -> bin/
        copy(self, "arno-fwfilter",
             src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        os.chmod(
            os.path.join(self.package_folder, "bin", "arno-fwfilter"),
            0o755,
        )

        # Environment + plugins -> share/arno-iptables-firewall/
        copy(self, "*",
             src=os.path.join(self.source_folder, "share", "arno-iptables-firewall"),
             dst=os.path.join(self.package_folder, "share", "arno-iptables-firewall"))

        # Configuration files -> etc/arno-iptables-firewall/
        copy(self, "*",
             src=os.path.join(self.source_folder, "etc", "arno-iptables-firewall"),
             dst=os.path.join(self.package_folder, "etc", "arno-iptables-firewall"))

        # Man pages -> share/man/
        copy(self, "*.8",
             src=os.path.join(self.source_folder, "share", "man", "man8"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "*.1",
             src=os.path.join(self.source_folder, "share", "man", "man1"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

        # License
        copy(self, "gpl_license.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["sbin", "bin"]
        self.cpp_info.resdirs = ["share", "etc"]
