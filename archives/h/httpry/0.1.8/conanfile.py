#!/usr/bin/env python3
"""Conan recipe for httpry 0.1.8 — HTTP logging and information retrieval tool.

Build system: Makefile (plain make, no configure).
Dependencies: libpcap, libm, pthread.
Patch: pthread_cancel replaced with cooperative flag-based cancellation (OHOS lacks pthread_cancel).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class HttpryConan(ConanFile):
    name = "httpry"
    version = "0.1.8"
    description = "HTTP logging and information retrieval tool"
    license = "GPL-2.0"
    homepage = "https://github.com/jbittel/httpry"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        pcap = self.dependencies["libpcap"]
        inc_dir = os.path.join(pcap.package_folder, "include")
        lib_dir = os.path.join(pcap.package_folder, "lib")
        # R9: always use -j1
        self.run(
            f'make -j1 '
            f'"CC={cc}" '
            f'"CCFLAGS=-Wall -O3 -funroll-loops -I{inc_dir}" '
            f'"LIBS=-L{lib_dir} -lpcap -lm -pthread"',
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "httpry", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "httpry.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
