#!/usr/bin/env python3
"""Conan recipe — mkhexgrid 0.1.1

mkhexgrid is a command-line tool that generates hex grids as PNG, PostScript,
or SVG. Given a center hex coordinate, it computes the pixel locations of the
vertices of a hex grid of arbitrary size.

Build system: plain Makefile (CC=g++, links -lgd), no configure, no test
target. Upstream has no test suite.
License: GPL-2.0-or-later (see COPYING).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class MkhexgridConan(ConanFile):
    name = "mkhexgrid"
    version = "0.1.1"
    description = "Generate hex grids as PNG, PostScript, or SVG from the command line"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nomic.net/~uckelman/mkhexgrid/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # boost is header-only here (only <boost/lexical_cast.hpp> is used)
        self.requires("boost/1.84.0", transitive_headers=True)
        # libgd provides gd.h and -lgd
        self.requires("gd/2.3.3", transitive_headers=True, transitive_libs=True)
        # boost/1.84.0 requires zlib/1.3.1, gd/2.3.3 requires zlib/1.3.1.1;
        # override to the newer version to resolve the conflict (see notes in
        # archives/a/abiword-plugin-docbook/3.0.8/conanfile.py for prior art).
        self.requires("zlib/1.3.1.1", override=True)

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
        from conan.tools.env import Environment
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = comp_execs.get("cpp") or "clang++"
        # Conan 2 API: iterate self.dependencies, read dep.cpp_info.
        # Inject dep include/lib paths via env vars (CPLUS_INCLUDE_PATH / LIBRARY_PATH)
        # so the Makefile's own CPPFLAGS (-DVERSION='"..."') stays untouched —
        # overriding it on the make command line breaks the quoting.
        # Also inject transitive deps (libpng, zlib) so static libgd.a can resolve
        # its png/z symbols at link time.
        env = Environment()
        for dep in self.dependencies.values():
            for incdir in dep.cpp_info.includedirs:
                env.prepend_path("CPLUS_INCLUDE_PATH", incdir)
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LIBRARY_PATH", libdir)
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        # Override only the compiler and stdlib flags; let Makefile CPPFLAGS stand.
        # OHOS uses libc++, not libstdc++ — replace -lstdc++ via LDFLAGS override.
        # Link: gd (static) + png16 + z (transitive deps of gd).
        # R9: -j1 for old single-binary make projects
        with env.vars(self).apply():
            self.run(
                f'make -j1 CXX="{cxx}" CC="{cxx}" '
                f'CXXFLAGS="-std=c++17 -stdlib=libc++" '
                f'LDFLAGS="-lm -lc++ -lgd -lpng16 -lz -stdlib=libc++"',
                cwd=self.source_folder,
            )

    def package(self):
        # mkhexgrid is a command-line tool: install the binary to bin/
        copy(self, "mkhexgrid", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
