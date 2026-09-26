#!/usr/bin/env python3
"""Conan recipe for lbt 1.2.2 - LTL to Buechi translator.

Builds the two upstream programs with the hand-written Makefile:

* ``lbt``     - reads an LTL formula on stdin, prints a generalized Buechi
                automaton (C++: Ltl.C/LtlGraph.C/BitVector.C/lbt.C)
* ``lbt2dot`` - converts the ``lbt`` output to GraphViz (C: lbt2dot.c)

Upstream tarball is only published over plain HTTP (www.tcs.hut.fi), so the
recipe uses Debian's verbatim ``.orig.tar.gz`` (same release, HTTPS, pinned
SHA-256).

The 2001 C++ sources use the ``register`` storage class (removed in C++17),
so the recipe builds them with ``-std=gnu++98``.  No upstream test suite exists;
``test_package`` exercises both filters on real input.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LbtConan(ConanFile):
    name = "lbt"
    version = "1.2.2"
    description = "Converts linear temporal logic (LTL) formulas to Buechi automata"
    license = "GPL-2.0-or-later"
    homepage = "http://www.tcs.hut.fi/Software/maria/tools/lbt/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lbt OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cxx = self._compiler("cpp", "clang++")
        cc = self._compiler("c", "clang")
        # Command-line CXXFLAGS/CFLAGS override the Makefile defaults, so the
        # upstream -fno-exceptions/-fno-rtti and -O3 are restated here.  gnu++98
        # is required for the `register` storage class used by BitVector.h.
        cxxflags = "-std=gnu++98 -O2 -fno-exceptions -fno-rtti -Wall"
        cflags = "-O2 -Wall"
        self.run('make CXX="{}" CC="{}" CXXFLAGS="{}" CFLAGS="{}" -j1'.format(
            cxx, cc, cxxflags, cflags), cwd=self.source_folder)
        for prog in ("lbt", "lbt2dot"):
            if not os.path.isfile(os.path.join(self.source_folder, prog)):
                raise ConanInvalidConfiguration(
                    "build did not produce the '{}' program".format(prog))

    def package(self):
        copy(self, "lbt", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "lbt2dot", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "lbt.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "lbt2dot.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "doc/*", self.source_folder,
             os.path.join(self.package_folder, "share", "doc", "lbt"))
        copy(self, "ChangeLog", self.source_folder,
             os.path.join(self.package_folder, "share", "doc", "lbt"))
        copy(self, "NEWS", self.source_folder,
             os.path.join(self.package_folder, "share", "doc", "lbt"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
