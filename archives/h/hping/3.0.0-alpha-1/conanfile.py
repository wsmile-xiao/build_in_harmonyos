#!/usr/bin/env python3
"""Conan recipe — hping 3.0.0-alpha-1 (network probing tool)."""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain

class HpingConan(ConanFile):
    name = "hping"
    version = "3.0.0-alpha-1"
    description = "hping — network probing tool (TCP/UDP/ICMP custom packets)"
    license = "GPL-2.0"
    homepage = "http://www.hping.org/"
    url = "https://github.com/antirez/hping"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
        pcap_dep = self.dependencies["libpcap"]
        pcap_inc = pcap_dep.cpp_info.includedirs[0] if pcap_dep.cpp_info.includedirs else ""
        pcap_lib = pcap_dep.cpp_info.libdirs[0] if pcap_dep.cpp_info.libdirs else ""
        self.run(f"CC={cc} ./configure --no-tcl", env="conanbuild")
        ccopt = f"-O2 -Wall -I{pcap_inc}"
        pcap_var = f"-L{pcap_lib} -lpcap"
        self.run(f"make -j1 CC={cc} CCOPT='{ccopt}' PCAP='{pcap_var}'", env="conanbuild")

    def package(self):
        copy(self, "hping3", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "docs/hping3.8", self.source_folder, os.path.join(self.package_folder, "share/man/man8"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
