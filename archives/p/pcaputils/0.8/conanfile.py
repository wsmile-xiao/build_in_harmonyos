#!/usr/bin/env python3
"""Conan recipe — pcaputils 0.8 (nongnu/Savannah pcap CLI tools).

Pure-Makefile project (no configure/CMake). Builds four command-line tools:
  pcapdump  -lpcap
  pcapip    -lpcap -lJudy
  pcappick  -lpcap
  pcapuc    -lpcap -lJudy
plus an internal static helper util/util.a (not shipped).

Build notes:
  * Upstream top-level Makefile hardcodes `CC = gcc` and has no install target;
    we override CC/AR/CFLAGS/LF_ALL on the make command line (R33: flags come
    from Conan toolchain/deps, not shell env), and copy binaries in package().
  * CFLAGS uses `?=` (overridable); LF_ALL is `=` but still overridable on the
    command line, which is how we inject -L for Conan deps.
  * No -lm needed (no libm calls); no shared internal lib exported.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PcaputilsConan(ConanFile):
    name = "pcaputils"
    version = "0.8"
    description = "nongnu/Savannah pcap packet-capture CLI tools (pcapdump/pcapip/pcappick/pcapuc)"
    license = "MIT"
    homepage = "https://download.savannah.nongnu.org/releases/pcaputils/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")
        self.requires("judy/1.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Inject Conan dep include/lib dirs on the make command line.
        pcap = self.dependencies["libpcap"].cpp_info
        judy = self.dependencies["judy"].cpp_info
        inc = " ".join(f"-I{d}" for d in pcap.includedirs)
        inc += " " + " ".join(f"-I{d}" for d in judy.includedirs)
        lib = " ".join(f"-L{d}" for d in pcap.libdirs)
        lib += " " + " ".join(f"-L{d}" for d in judy.libdirs)
        # R33: compiler/flags explicit on command line, not via shell env.
        self.run(
            f"make CC=clang AR=llvm-ar -j1 "
            f"CFLAGS='-O2 -ggdb -Wall {inc}' "
            f"LF_ALL='-rdynamic {lib} -Wl,--as-needed -Wl,-z,defs'",
            cwd=self.source_folder,
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for tool in ("pcapdump", "pcapip", "pcappick", "pcapuc"):
            copy(self, tool,
                 src=os.path.join(self.source_folder, "src"),
                 dst=bindir,
                 keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
