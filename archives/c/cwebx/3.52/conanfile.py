#!/usr/bin/env python3
"""Conan recipe for CWEBx x3.52 — literate programming tools ctanglex/cweavex.

CWEBx is Marc van Leeuwen's ANSI-C branch of CWEB. The release is a raw Makefile
project: its ./configure is an 82-byte notice script, not an autotools generator.
cweave.c is not shipped, so the build bootstraps it by running the freshly built
./ctanglex — which works on OHOS because the SDK clang already emits the
.codesign section at link time (no extra signing step).
"""
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


def _c_compiler(conanfile):
    # R33: take the compiler from the Conan profile, never from shell variables.
    executables = conanfile.conf.get("tools.build:compiler_executables",
                                     default={}, check_type=dict) or {}
    return executables.get("c", "clang")


class CwebxConan(ConanFile):
    name = "cwebx"
    version = "3.52"
    description = ("CWEBx literate programming system for ANSI C/C++: ctanglex "
                   "extracts C sources and cweavex extracts TeX from .w files")
    license = "Knuth-CTAN"
    homepage = "http://wwwmathlabo.univ-poitiers.fr/~maavl/CWEBx/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # needs only a C compiler and libc; no third-party dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # `cweb` is the upstream target for the two binaries. The default `all`
        # target additionally runs TeX over manual.tex and typesets the source
        # listings, and the platform ships no TeX.
        self.run(f"make cweb CC={_c_compiler(self)} -j1", cwd=self.source_folder)

    def package(self):
        # The upstream install target copies both binaries into $(prefix)/bin and
        # creates that directory itself, so `prefix` alone stages into the package.
        self.run(f"make install prefix={self.package_folder} "
                 f"CC={_c_compiler(self)}", cwd=self.source_folder)
        copy(self, "cwebxmac.tex", self.source_folder,
             os.path.join(self.package_folder, "share", "texmf", "tex", "generic"))
        copy(self, "cwebcmac.tex", self.source_folder,
             os.path.join(self.package_folder, "share", "texmf", "tex", "generic"))
        copy(self, "cwebhmac.tex", self.source_folder,
             os.path.join(self.package_folder, "share", "texmf", "tex", "generic"))
        copy(self, "cweb.1", os.path.join(self.source_folder, "man1"),
             os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
