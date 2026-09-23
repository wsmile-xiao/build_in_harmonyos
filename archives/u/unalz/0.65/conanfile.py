#!/usr/bin/env python3
"""Conan recipe — unalz 0.65

Command-line extractor for ALZ archives (AlZip, Korean archive format).
Upstream: kippler (http://www.kipple.pe.kr), plain-Makefile project, no
configure script and no upstream test suite.

Build system: upstream Makefile with per-system targets. The ``linux-utf8``
target is the right one for OHOS: it enables the iconv filename-conversion
path (-D_UNALZ_ICONV -D_UNALZ_UTF8) without ``-liconv`` (musl provides
iconv in libc). zlib/bzip2 are bundled subsets in the tarball, so the
package has no external requirements.

Compiler is taken from Conan conf (tools.build:compiler_executables) and
passed as make command-line variables because the Makefile hardcodes
``CC = gcc`` / ``CPP = g++`` (make command-line variables override the
in-file assignments; R33: never rely on bare shell env vars).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class UnalzConan(ConanFile):
    name = "unalz"
    version = "0.65"
    description = (
        "unalz — command-line extractor for ALZ archives "
        "(AlZip format, with EUC-KR/CP949 filename conversion)"
    )
    license = "Zlib AND bzip2-1.0.6"  # unalz itself: zlib license; bundled zlib + bzip2 subsets
    homepage = "http://www.kipple.pe.kr/win/unalz/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # zlib/bzip2 subsets are bundled in the upstream tarball

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: get compilers from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        cxx = comp_execs.get("cpp") or "clang++"
        # linux-utf8: iconv + UTF-8 filename output, no -liconv (musl has iconv in libc).
        # CC/CPP/CXX as make command-line variables override the hardcoded gcc/g++.
        # R9: -j1 for this small single-shot make project.
        self.run(
            f'make -j1 linux-utf8 CC="{cc}" CXX="{cxx}" CPP="{cxx}"',
            cwd=self.source_folder,
        )

    def package(self):
        # unalz is a command-line tool: install the binary to bin/.
        # (upstream `make install` hardcodes /usr/local/bin — never used, R49)
        copy(self, "unalz", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
