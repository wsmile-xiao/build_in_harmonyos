#!/usr/bin/env python3
"""Conan recipe for miniasm 0.3 — a fast OLC de novo assembler for long reads.

miniasm takes all-vs-all read overlaps (PAF) and outputs an assembly graph in
GFA. It is plain C with a Makefile and needs zlib, libm and pthread (pthread
is part of bionic libc on OHOS). This recipe compiles the upstream translation
units directly and links against the Conan zlib package.

A `source()` is provided, but since some `conan create` configurations skip it
when the cache source folder already exists, `build()` re-fetches the tarball
if the translation units are missing.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    unzip,
)
from conan.tools.layout import basic_layout

_OBJECTS = ("sys", "sdict", "paf", "asg", "common", "hit", "asm", "main")


class MiniasmConan(ConanFile):
    name = "miniasm"
    version = "0.3"
    description = "Fast OLC de novo assembler for noisy long reads (PAF -> GFA)"
    license = "MIT"
    homepage = "https://github.com/lh3/miniasm"
    url = "https://github.com/lh3/miniasm"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def _fetch_sources(self, destination):
        """Download and extract the pinned tarball into ``destination``."""
        sources = self.conan_data["sources"]
        # self.build_folder is None while source() runs, so keep the tarball
        # next to the extraction target.
        tarball = os.path.join(destination, ".miniasm-src.tar.gz")
        download(self, url=sources["url"], filename=tarball,
                 sha256=sources["sha256"], verify=True)
        unzip(self, tarball, destination=destination, strip_root=True)

    def source(self):
        self._fetch_sources(self.source_folder)

    def generate(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        self._cc = str(executables.get("c") or "clang")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # Guard: some conan create paths skip source(), leaving it empty.
        if not os.path.isfile(os.path.join(src, "sys.c")):
            self._fetch_sources(src)

        build = self.build_folder
        zlib = self.dependencies["zlib"].cpp_info
        z_inc = zlib.includedirs[0]
        z_lib = zlib.libdirs[0]
        opt = "-O2" if self.settings.build_type == "Release" else "-g -O0"

        objects = []
        for name in _OBJECTS:
            obj = os.path.join(build, name + ".o")
            objects.append(obj)
            self.run(
                f'{self._cc} -c {opt} -Wall -I "{src}" -I "{z_inc}" '
                f'-o "{obj}" "{src}/{name}.c"'
            )
        link = " ".join(f'"{obj}"' for obj in objects)
        self.run(f'{self._cc} {opt} -o "{build}/miniasm" {link} -L "{z_lib}" -lz -lm')

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(man_dir, exist_ok=True)
        copy(self, "miniasm", src=self.build_folder, dst=bin_dir, keep_path=False)
        os.chmod(os.path.join(bin_dir, "miniasm"), 0o755)
        copy(self, "miniasm.1", src=self.source_folder, dst=man_dir, keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
