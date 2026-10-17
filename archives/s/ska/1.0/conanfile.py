#!/usr/bin/env python3
"""Conan recipe — ska 1.0

SKA (Split Kmer Analysis) — toolkit for prokaryotic DNA sequence analysis
using split kmers (bacterial genomic epidemiology / outbreak investigation).

Build system: plain Makefile (upstream Makefile, C++11, links -lz), no
configure step. Produces a single executable `bin/ska` with subcommands
(fasta/fastq/align/distance/map/merge/...).

Requires zlib (upstream links -lz).
License: MIT (upstream LICENSE).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SkaConan(ConanFile):
    name = "ska"
    version = "1.0"
    description = "SKA (Split Kmer Analysis) — split-kmer toolkit for bacterial genomic epidemiology"
    license = "MIT"
    homepage = "https://github.com/simonrharris/SKA"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream Makefile links -lz (gzstream/kseq gzip input/output support)
        self.requires("zlib/1.3.1")

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
        # R33: compiler and flags must come from Conan conf / dependency graph,
        # never from bare shell env vars (release workers have them unset).
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = comp_execs.get("cpp") or "clang++"
        zinfo = self.dependencies["zlib"].cpp_info
        z_inc = zinfo.includedirs[0]
        z_lib = zinfo.libdirs[0]
        # R9: single -j1 for this small plain-Makefile project.
        # R26: zlib is a system-same-name library — Conan default provides
        # the static archive (libz.a), no /lib,/lib64 pollution.
        self.run(
            f'make -j1 CXX="{cxx}" '
            f'CXXFLAGS="-O2 -std=c++0x -I{z_inc}" '
            f'LDFLAGS="-L{z_lib} -lz"',
            cwd=self.source_folder,
        )

    def package(self):
        # ska is a command-line tool: install the binary to bin/
        copy(self, "ska", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
