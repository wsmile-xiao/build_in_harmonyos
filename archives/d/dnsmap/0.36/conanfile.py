#!/usr/bin/env python3
"""Conan recipe — dnsmap 0.36.

DNS subdomain enumeration tool (pure C, single source file).
Build: manual (upstream uses autotools; OHOS builds single file directly).
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class DnsmapConan(ConanFile):
    name = "dnsmap"
    version = "0.36"
    package_type = "application"

    description = "DNS subdomain enumeration tool (pure C, std POSIX only)"
    homepage = "https://github.com/resurrecting-open-source-projects/dnsmap"
    license = "GPL-2.0-or-later"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # 手动编译单文件（src/Makefile.am: dnsmap_SOURCES = dnsmap.c）
        src = self.source_folder
        bld = self.build_folder
        self.run(f"cd {src} && clang -O2 -fPIC -o {bld}/dnsmap src/dnsmap.c")

    def package(self):
        bld = self.build_folder
        copy(self, "dnsmap", src=bld,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []