#!/usr/bin/env python3
"""Conan recipe for aconf-mod-dns-zone 0.8.1."""

import os

from conan import ConanFile
from conan.tools.files import (
    get,
    copy,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.layout import basic_layout


class AconfModDnsZoneConan(ConanFile):
    name = "aconf-mod-dns-zone"
    version = "0.8.1"

    description = "DNS zone configuration module for aconf"
    license = "MIT"
    homepage = "https://gitlab.alpinelinux.org/alpinelinux/aconf"
    url = "https://gitlab.alpinelinux.org/alpinelinux/aconf"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aconf/0.8.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
        )

    def build(self):
        # 当前无补丁，调用保留用于满足仓库标准配方流程。
        apply_conandata_patches(self)

    def package(self):
        copy(
            self,
            "dns-zone.lua",
            src=os.path.join(
                self.source_folder,
                "aconf",
                "modules",
            ),
            dst=os.path.join(
                self.package_folder,
                "usr",
                "share",
                "lua",
                "5.4",
                "aconf",
                "modules",
            ),
        )

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
