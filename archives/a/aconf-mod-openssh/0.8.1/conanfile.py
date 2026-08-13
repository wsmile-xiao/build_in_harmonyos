#!/usr/bin/env python3
"""Conan recipe for aconf-mod-openssh 0.8.1."""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AconfModOpensshConan(ConanFile):
    name = "aconf-mod-openssh"
    version = "0.8.1"

    description = "OpenSSH configuration module for aconf"
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
        # 按仓库标准流程应用 conandata 中声明的补丁。
        # 当前 patches 为空，因此这里实际为 no-op。
        apply_conandata_patches(self)

    def package(self):
        src = os.path.join(
            self.source_folder,
            "aconf",
            "modules",
        )

        dst = os.path.join(
            self.package_folder,
            "usr",
            "share",
            "lua",
            "5.4",
            "aconf",
            "modules",
        )

        copy(
            self,
            "openssh.lua",
            src=src,
            dst=dst,
        )

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
