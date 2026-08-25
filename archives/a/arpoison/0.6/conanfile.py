#!/usr/bin/env python3
"""Conan recipe for arpoison 0.6 — ARP poison tool.

Build system: Makefile (simple single-file C program, not autotools/cmake).
Depends on: libnet/1.2 (for ARP packet construction API).
Product: command-line tool (binary), not a library.
Adapted for HarmonyOS PC (arm64) platform.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.gnu import AutotoolsToolchain


class ArpoisonConan(ConanFile):
    name = "arpoison"
    version = "0.6"
    description = "ARP poison tool — sends custom ARP REPLY packets"
    license = "GPL-2.0"
    homepage = "http://arpoison.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libnet/1.2")

    def layout(self):
        basic_layout(self)

    def generate(self):
        # R33: AutotoolsToolchain sets CC/CXX/CFLAGS from Conan profile
        tc = AutotoolsToolchain(self)
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        # R32: settings.os check must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"arpoison only supports Linux and OHOS, got {self.settings.os}"
            )

    def build(self):
        apply_conandata_patches(self)

        # Get libnet dependency paths from Conan 2 API
        libnet = self.dependencies["libnet"]
        cpp_info = libnet.cpp_info

        # Resolve include and lib directories (may be relative to package folder)
        pkg_folder = libnet.package_folder
        include_dirs = []
        for d in cpp_info.includedirs:
            include_dirs.append(d if os.path.isabs(d) else os.path.join(pkg_folder, d))

        lib_dirs = []
        for d in cpp_info.libdirs:
            lib_dirs.append(d if os.path.isabs(d) else os.path.join(pkg_folder, d))

        include_flags = " ".join([f"-I{d}" for d in include_dirs])
        lib_flags = " ".join([f"-L{d}" for d in lib_dirs]) + " -lnet"

        # Use full paths for source and output (R33: Conan build env for compiler)
        arpoison_src = os.path.join(self.source_folder, "arpoison.c")
        arpoison_out = os.path.join(self.build_folder, "arpoison")

        # lld from OHOS SDK requires libxml2.so.16 (missing); use GNU ld instead
        fuse_ld = "-fuse-ld=/data/service/hnp/bin/ld" if str(self.settings.os) == "OHOS" else ""

        self.run(
            f"$CC $CFLAGS -Wall -D_BSD_SOURCE -D_DEFAULT_SOURCE -DHAVE_NET_ETHERNET_H "
            f"{include_flags} {arpoison_src} -o {arpoison_out} {lib_flags} {fuse_ld}",
            env="conanbuild",
        )

    def package(self):
        copy(self, "arpoison", dst=os.path.join(self.package_folder, "bin"), src=self.build_folder)
        copy(self, "arpoison.8", dst=os.path.join(self.package_folder, "share", "man", "man8"), src=self.source_folder)

    def package_info(self):
        # arpoison is a command-line tool, not a library
        self.cpp_info.bindirs = ["bin"]
