#!/usr/bin/env python3
"""Conan recipe — vlevel 0.5.2 (upstream recursive Makefile, CLI audio filter).

VLevel is a dynamic volume normalizer. Only the core components are built:
volumeleveler/ (the leveling algorithm object) and vlevel-bin/ (the raw
PCM stdin/stdout filter CLI). The optional plugin frontends (vlevel-ladspa,
vlevel-jack, vlevel-winamp) require host environment headers/toolchains
that OHOS does not provide and are intentionally skipped.

Upstream ships no test suite; the consumer test pipes real raw PCM through
the packaged binary and asserts the filter's behavior.
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


class VlevelConan(ConanFile):
    name = "vlevel"
    version = "0.5.2"
    description = "VLevel — a dynamic volume normalizer (raw PCM filter CLI)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/radiocicletta/vlevel"
    url = ""  # CI fills this
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        cxxflags = (
            f'-Wall -O3 -fPIC -DPIC -DVLEVEL_VERSION=\\"{self.version}\\"'
        )
        # volumeleveler.o is built on demand by vlevel-bin/Makefile; only the
        # core pair is built (see docstring for the skipped plugin frontends).
        self.run(
            f'make -C vlevel-bin -j2 CXX={cxx} VERSION={self.version} '
            f"CXXFLAGS='{cxxflags}'",
            cwd=self.source_folder,
        )

    def package(self):
        src = self.source_folder
        dist = os.path.join(src, "conan-dist")
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        # Upstream `install` assumes $(PREFIX)/bin already exists.
        os.makedirs(os.path.join(dist, "bin"), exist_ok=True)
        self.run(
            f"make -C vlevel-bin install PREFIX={dist} CXX={cxx} "
            f"VERSION={self.version}",
            cwd=src,
        )
        copy(self, "bin/*", src=dist,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=src,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
