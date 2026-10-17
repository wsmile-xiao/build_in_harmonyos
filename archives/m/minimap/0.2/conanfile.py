#!/usr/bin/env python3
"""Conan recipe for minimap 0.2 — fast approximate long-read mapper.

minimap finds approximate mapping positions between two sets of long
sequences. The package ships the `minimap` CLI, the `libminimap.a` static
library and the public headers (minimap.h, bseq.h, kseq.h). It needs zlib and
libm (pthread is part of bionic libc on OHOS).

A `source()` is provided; `build()` re-fetches the tarball if a conan create
configuration skipped source() and left the source folder empty.
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

_LIB_OBJECTS = ("kthread", "misc", "bseq", "sketch", "sdust", "index", "map")


class MinimapConan(ConanFile):
    name = "minimap"
    version = "0.2"
    description = "Fast approximate mapping of long sequences (minimizer-based)"
    license = "MIT"
    homepage = "https://github.com/lh3/minimap"
    url = "https://github.com/lh3/minimap"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def _fetch_sources(self, destination):
        sources = self.conan_data["sources"]
        tarball = os.path.join(destination, ".minimap-src.tar.gz")
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
        self._ar = str(executables.get("ar") or "ar")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        if not os.path.isfile(os.path.join(src, "minimap.h")):
            self._fetch_sources(src)

        build = self.build_folder
        zlib = self.dependencies["zlib"].cpp_info
        z_inc = zlib.includedirs[0]
        z_lib = zlib.libdirs[0]
        opt = "-O2" if self.settings.build_type == "Release" else "-g -O0"

        objects = []
        for name in _LIB_OBJECTS:
            obj = os.path.join(build, name + ".o")
            objects.append(obj)
            self.run(
                f'{self._cc} -c {opt} -Wall -I "{src}" -I "{z_inc}" '
                f'-o "{obj}" "{src}/{name}.c"'
            )
        self.run(
            f'{self._ar} rcs "{build}/libminimap.a" '
            + " ".join(f'"{obj}"' for obj in objects)
        )
        self.run(
            f'{self._cc} -c {opt} -Wall -I "{src}" -I "{z_inc}" '
            f'-o "{build}/main.o" "{src}/main.c"'
        )
        self.run(
            f'{self._cc} {opt} -o "{build}/minimap" "{build}/main.o" '
            f'-L "{build}" -lminimap -L "{z_lib}" -lz -lm'
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        for path in (bin_dir, lib_dir, inc_dir, man_dir):
            os.makedirs(path, exist_ok=True)
        copy(self, "minimap", src=self.build_folder, dst=bin_dir, keep_path=False)
        os.chmod(os.path.join(bin_dir, "minimap"), 0o755)
        copy(self, "libminimap.a", src=self.build_folder, dst=lib_dir, keep_path=False)
        for header in ("minimap.h", "bseq.h", "kseq.h"):
            copy(self, header, src=self.source_folder, dst=inc_dir, keep_path=False)
        copy(self, "minimap.1", src=self.source_folder, dst=man_dir, keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["minimap"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "minimap")
        self.cpp_info.set_property("cmake_target_name", "minimap::minimap")
