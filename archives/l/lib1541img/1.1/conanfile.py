#!/usr/bin/env python3
"""Conan recipe for lib1541img 1.1 — C library for Commodore 1541 (.d64) disk
images (BSD-2-Clause).

The upstream build uses GNU make via the `zimk` git submodule (not present in
the release tarball), so this recipe compiles the C translation units directly
into lib1541img.a and installs the public headers include/1541img/*.h.

Upstream ships no test suite; the test_package exercises the API end to end
(create image -> add a file -> write -> read back and verify).
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

_MODULES = (
    "util", "log", "sector", "track", "d64", "zc45reader", "filedata",
    "hostfilereader", "hostfilewriter", "d64writer", "filename", "zcfileset",
    "zc45extractor", "cbmdosfile", "cbmdosvfs", "cbmdosvfsreader", "d64reader",
    "zc45writer", "zc45compressor", "event", "cbmdosfs", "lynx", "petscii",
)


class Lib1541imgConan(ConanFile):
    name = "lib1541img"
    version = "1.1"
    description = "C library for creating and modifying Commodore 1541 (.d64) disk images"
    license = "BSD-2-Clause"
    homepage = "https://github.com/excess-c64/lib1541img"
    url = "https://github.com/excess-c64/lib1541img"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        self._cc = str(executables.get("c") or "clang")
        ar = executables.get("ar") or ""
        if not ar:
            cc_path = str(executables.get("c") or "").strip()
            if cc_path:
                bindir = os.path.dirname(cc_path)
                for cand in ("llvm-ar", "ar"):
                    full = os.path.join(bindir, cand)
                    if os.path.isfile(full):
                        ar = full
                        break
        self._ar = str(ar or "ar")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        build = self.build_folder
        inc = os.path.join(src, "include")
        libsrc = os.path.join(src, "src", "lib", "1541img")
        opt = "-O2" if self.settings.build_type == "Release" else "-g -O0"

        objects = []
        for name in _MODULES:
            obj = os.path.join(build, name + ".o")
            objects.append(obj)
            self.run(
                f'{self._cc} -c {opt} -std=c11 -DBUILDING_1541IMG -I "{inc}" '
                f'-o "{obj}" "{libsrc}/{name}.c"'
            )
        self.run(
            f'{self._ar} rcs "{build}/lib1541img.a" '
            + " ".join(f'"{obj}"' for obj in objects)
        )

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "include", "1541img"),
             dst=os.path.join(self.package_folder, "include", "1541img"))
        copy(self, "lib1541img.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["1541img"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "1541img")
        self.cpp_info.set_property("cmake_target_name", "1541img::1541img")
