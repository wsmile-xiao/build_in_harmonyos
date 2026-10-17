#!/usr/bin/env python3
"""Conan recipe — dhcpdump 1.10 (makefile, binary tool)."""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DhcpdumpConan(ConanFile):
    name = "dhcpdump"
    version = "1.10"
    description = "Parse DHCP packets from a network interface."
    license = "BSD-2-Clause"
    homepage = "https://github.com/bbonev/dhcpdump"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cppflags = " ".join(f"-I{dir}" for dir in self.dependencies["libpcap"].cpp_info.includedirs)
        # R8: Makefile uses UDP_LEN_F=len on __linux__ but OHOS udphdr has uh_ulen.
        # Inject via CPPFLAGS so Makefile CFLAGS/LDFLAGS hardening remains intact.
        if self.settings.os == "OHOS":
            cppflags += " -DUDP_LEN_F=uh_ulen"
        libdirs = " ".join(f"-L{dir}" for dir in self.dependencies["libpcap"].cpp_info.libdirs)
        libs = f"{libdirs} -lpcap"
        self.run(f'cd "{self.source_folder}" && make CC={cc} "CPPFLAGS={cppflags}" "LIBS={libs}" -j1')

    def package(self):
        copy(self, "dhcpdump", self.source_folder, str(self.package_folder) + "/bin")
        copy(self, "dhcpdump.8", self.source_folder, str(self.package_folder) + "/share/man/man8")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]