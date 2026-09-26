#!/usr/bin/env python3
"""Conan recipe — fastahack 1.0.0 (Erik Garrison's fast FASTA indexer).

fastahack is a small command-line application for indexing and extracting
sequences/subsequences from FASTA files.  It also bundles the Fasta.cpp
reader/indexer library, but the upstream build only produces the CLI binary.

Build system: pure Makefile (no configure script).
  - CXX defaults to g++ upstream → override with clang++ from Conan conf (R33).
  - CXXFLAGS upstream: -O3 -D_FILE_OFFSET_BITS=64.  We keep -D_FILE_OFFSET_BITS=64
    (LFS) and add -fPIC for shared-code compatibility.
  - OHOS musl libc does not define the glibc-private ``__off64_t`` typedef;
    the bundled LargeFileSupport.h is patched to use the standard ``off_t``
    (equivalent under _FILE_OFFSET_BITS=64).
  - install target: ``make install DESTDIR=<dir> PREFIX=/usr/local`` copies
    the single ``fastahack`` executable into <dir>/usr/local/bin.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class FastahackConan(ConanFile):
    name = "fastahack"
    version = "1.0.0"
    description = "fastahack: fast FASTA file indexing, subsequence and sequence extraction"
    license = "MIT"
    homepage = "https://github.com/ekg/fastahack"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # R38: command-line tool (single executable), not a library.
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # Simple in-source build; no CMake/Meson build folder split.
        self.folders.build = "."

    def source(self):
        # codeload tag URL 末段为 v1.0.0（无 .tar.gz 扩展名），
        # 显式指定 filename 让 conan get() 按 gzip/tar 解压。
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="fastahack-1.0.0.tar.gz")

    def build(self):
        # Apply patches declared in conandata.yml (OHOS off_t fix).
        apply_conandata_patches(self)

        # R33: get compiler from Conan conf, never from shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = comp_execs.get("cxx", "clang++") if isinstance(comp_execs, dict) else "clang++"

        # Upstream CFLAGS plus -fPIC (R33: no shell env vars).
        cxxflags = "-O3 -fPIC -D_FILE_OFFSET_BITS=64"

        # R9: always -j1.
        self.run(
            f'make CXX="{cxx}" CXXFLAGS="{cxxflags}" -j1',
            env="conanbuild",
        )

    def package(self):
        # 'make install DESTDIR=<dir> PREFIX=/usr/local' installs into
        # <dir>/usr/local/bin/fastahack.
        self.run(f'make install DESTDIR="{self.package_folder}" PREFIX=/usr/local')
        # Fallback: if the install target produced nothing, copy directly.
        bin_dir = os.path.join(self.package_folder, "usr", "local", "bin")
        if not os.path.exists(bin_dir) or not os.listdir(bin_dir):
            os.makedirs(bin_dir, exist_ok=True)
            copy(self, "fastahack", src=self.build_folder, dst=bin_dir)

    def package_info(self):
        # Single CLI executable.
        self.cpp_info.bindirs = ["usr/local/bin"]
        self.cpp_info.libdirs = []
