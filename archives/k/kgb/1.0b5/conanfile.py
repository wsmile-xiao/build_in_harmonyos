#!/usr/bin/env python3
"""Conan recipe for kgb 1.0b5 - KGB archiver (PAQ6 based).

A single C++ source file built by a hand-written Makefile.  The Makefile's
default ``CXXFLAGS`` already define ``PROGNAME`` and select ``-std=c++0x``;
only ``CXX`` needs to be pointed at the OHOS clang++ and the default
``LDFLAGS=-s`` is dropped so the toolchain's linker/strip are used.

Upstream ships no test suite (no ``make check``), so ``test_package`` provides
the consumer coverage, including a byte-exact round-trip.

Note: the archive format depends on ``PROGNAME`` (the ``MAGIC`` Makefile
variable, ``KGB_arch``); the recipe keeps the upstream default.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class KgbConan(ConanFile):
    name = "kgb"
    version = "1.0b5"
    description = "Archiver for .kgb files (high-ratio PAQ6 based compressor)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/FS-make-simple/kgb/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kgb OHOS adaptation is validated on Linux/OHOS, not "
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
        # CI injects CXXFLAGS (currently -fPIC -O2).  Upstream uses
        # `CXXFLAGS ?= ...`, so that environment value suppresses its required
        # -DPROGNAME and -std=c++0x defaults.  Pass the complete flags here so
        # archive magic remains KGB_arch in both CI and local builds.
        cxxflags = '-fPIC -O2 -Wall -std=c++0x -O3 -DPROGNAME=\'"KGB_arch"\''
        command = "make CXX={} CXXFLAGS={} LDFLAGS= -j1".format(
            shlex.quote(cxx), shlex.quote(cxxflags))
        self.run(command, cwd=self.source_folder)
        if not os.path.isfile(os.path.join(self.source_folder, "kgb")):
            raise ConanInvalidConfiguration("build did not produce the 'kgb' program")

    def package(self):
        copy(self, "kgb", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder,
             os.path.join(self.package_folder, "share", "doc", "kgb"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
