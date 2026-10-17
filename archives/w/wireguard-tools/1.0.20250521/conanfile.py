#!/usr/bin/env python3
"""Conan recipe — wireguard-tools 1.0.20250521 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class WireguardToolsConan(ConanFile):
    name = "wireguard-tools"
    version = "1.0.20250521"
    description = "WireGuard is an extremely simple yet fast and modern VPN tunnel"
    license = "GPL-2.0"
    homepage = "https://www.wireguard.com/"
    url = "https://github.com/WireGuard/wireguard-tools"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src_dir = os.path.join(self.source_folder, "src")
        self.run(f"cd {src_dir} && make CC=clang -j1 WITH_WGQUICK=no")

    def package(self):
        copy(self, "wg", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "wg.8", os.path.join(self.source_folder, "src", "man"),
             os.path.join(self.package_folder, "share", "man", "man8"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
