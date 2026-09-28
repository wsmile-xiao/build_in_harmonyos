#!/usr/bin/env python3
"""Conan recipe — ipaddress 1.2.1 (header-only C++ library).

ipaddress is a C++ header-only (CMake INTERFACE) library for working with
IPv4/IPv6 addresses and networks. Upstream builds via CMake and installs
include/ headers plus CMake package config and pkg-config file. There is no
compiled artifact, so this recipe follows the header-only variant: copy the
headers, clear bindirs/libdirs, and keep a single package_id.
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class IpaddressConan(ConanFile):
    name = "ipaddress"
    version = "1.2.1"
    description = "A C++ library for working and manipulating IPv4/IPv6 addresses and networks"
    license = "MIT"
    homepage = "https://github.com/VladimirShaleev/ipaddress"
    url = ""  # CI fills this

    package_type = "header-library"

    # Header-only: no compiled artifact, but keep settings for structural consistency
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only INTERFACE library: nothing to compile. Apply any
        # declared patches (none upstream), then no build steps.
        apply_conandata_patches(self)

    def package(self):
        copy(
            self,
            "*.hpp",
            src=self.source_folder,
            dst=self.package_folder,
        )
        copy(
            self,
            "*.h",
            src=self.source_folder,
            dst=self.package_folder,
        )
        copy(self, "LICENSE*", src=self.source_folder,
             dst="licenses", keep_path=False)

    def package_id(self):
        self.info.clear()          # no compiled deps on os/compiler -> single package_id

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
