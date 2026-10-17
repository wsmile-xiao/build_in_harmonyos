#!/usr/bin/env python3
"""Conan recipe for arpalert 2.0.12 — ARP network monitoring tool.

arpalert monitors ARP traffic and can detect new/unknown devices on the network.
This is a command-line tool (not a library), so package_type = "application".
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ArpalertConan(ConanFile):
    name = "arpalert"
    version = "2.0.12"
    description = "ARP alert network monitoring tool — detects new/unknown devices via ARP traffic"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/thierry-f-78/arpalert"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_cflags.append("-fcommon")
        # Add libpcap include and lib paths for configure header checks
        pcap_dep = self.dependencies["libpcap"]
        pcap_root = pcap_dep.package_folder
        tc.extra_cflags.append(f"-I{os.path.join(pcap_root, 'include')}")
        tc.extra_ldflags.append(f"-L{os.path.join(pcap_root, 'lib')}")
        tc.configure_args.append("--with-syslog")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS/SELinux does not preserve +x on extracted files.
        # Run configure with bash explicitly from the source directory.
        # Also run make from the source directory since Makefile uses src_dir=.
        configure_args = [
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
            "--with-syslog",
        ]
        args_str = " ".join(configure_args)
        with chdir(self, self.source_folder):
            self.run(f"bash ./configure {args_str}", env="conanbuild")
            self.run("make -j1", env="conanbuild")

    def package(self):
        # Install with DESTDIR pointing to the Conan package folder
        with chdir(self, self.source_folder):
            self.run(f"make install DESTDIR={self.package_folder}", env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.includedirs = ["include"]
