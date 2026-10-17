#!/usr/bin/env python3
"""Conan recipe for inih-inireader 62 — the inih C parser plus the INIReader
C++ wrapper, built as static libraries.

Upstream tag ``r62`` ships:
  * ini.c / ini.h        — the C INI parser (library ``inih``)
  * cpp/INIReader.cpp/h  — the C++ ``INIReader`` class (library ``INIReader``)

Upstream is Meson based, but this worker builds the two translation units
directly with clang (as done for inih/r58): no external dependency, only the
C / C++ standard library.
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


class InihInireaderConan(ConanFile):
    name = "inih-inireader"
    version = "62"
    description = "inih simple INI parser (C) plus the INIReader C++ wrapper"
    license = "BSD-3-Clause"
    homepage = "https://github.com/benhoyt/inih"
    url = "https://github.com/benhoyt/inih"

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
        """Collect compiler / archiver paths from the Conan profile (R33)."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        self._cc = str(executables.get("c") or "clang")
        self._cxx = str(executables.get("cpp") or "clang++")
        ar = executables.get("ar") or ""
        if not ar:
            cc_path = str(executables.get("c") or "").strip()
            if cc_path:
                bindir = os.path.dirname(cc_path)
                for candidate in ("llvm-ar", "ar"):
                    full = os.path.join(bindir, candidate)
                    if os.path.isfile(full):
                        ar = full
                        break
        self._ar = str(ar or "ar")

    def _cflags(self):
        return "-O2" if self.settings.build_type == "Release" else "-g -O0"

    def build(self):
        apply_conandata_patches(self)
        root = self.source_folder
        build_dir = self.build_folder
        cflags = self._cflags()

        # C parser -> libinih.a
        self.run(f'{self._cc} -c {cflags} -o "{build_dir}/ini.o" "{root}/ini.c"')
        self.run(f'{self._ar} rcs "{build_dir}/libinih.a" "{build_dir}/ini.o"')

        # C++ wrapper -> libINIReader.a (links against inih at consumer side)
        self.run(
            f'{self._cxx} -c {cflags} -std=c++11 '
            f'-I "{root}" -I "{root}/cpp" '
            f'-o "{build_dir}/INIReader.o" "{root}/cpp/INIReader.cpp"'
        )
        self.run(
            f'{self._ar} rcs "{build_dir}/libINIReader.a" "{build_dir}/INIReader.o"'
        )

    def package(self):
        copy(self, "ini.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "INIReader.h", src=os.path.join(self.source_folder, "cpp"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libinih.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libINIReader.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        # Link order matters for static archives: INIReader first, then inih.
        self.cpp_info.libs = ["INIReader", "inih"]
        self.cpp_info.set_property("cmake_file_name", "inih-inireader")
        self.cpp_info.set_property("cmake_target_name", "inih-inireader::inih-inireader")
