#!/usr/bin/env python3
"""Conan recipe for cba 0.3.6 (Continuous Beam Analysis) — CLI tool.

cba calculates member forces and support reactions of a continuous beam.
Pure-C++ plain-Makefile project: the command-line solver lives in src/
(cbeam_class.cpp + cba_main.cpp -> "cba"); the wxWidgets GUI (src/gui,
wxCBA/cba-gtk) is an independent Makefile target that is intentionally NOT
built — CLI-only adaptation. Upstream 0.3.6 has no configure script at all,
so "disable-wx" style switches do not exist; the two parts are separated at
Makefile level (Debian also builds the CLI and the GUI separately).

Source: upstream official release on SourceForge (project cbeam,
"cba-0.3.6-linux.tar.gz") — sources identical to the Debian orig repack
(which only strips the prebuilt x86 binaries).

Upstream ships NO test suite (no tests/ dir, no make check/TESTS target,
no configure.ac). Coverage is provided by the test_package harness:
11 cases / 55 assertions — 6 structural-analysis analytic checks
(41 assertions), 4 CLI parameter/error-path cases (8 assertions),
1 -o/-p output/plot consistency case (6 assertions).
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, chdir, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CbaConan(ConanFile):
    name = "cba"
    version = "0.3.6"
    description = ("Continuous Beam Analysis — member forces and support "
                   "reactions of a continuous beam (CLI)")
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/cbeam/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler comes from the Conan profile conf, never from shell env.
        cxx = (self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict) or {}).get("cpp", "clang++")
        with chdir(self, self.source_folder):
            # CLI-only: build src/ (the "cba" CLI). src/gui (wxCBA GUI, needs
            # wxWidgets/wx-config) is deliberately skipped — upstream separates
            # CLI and GUI at Makefile level, there is no configure switch.
            # The Makefile hardcodes "CXX := c++", so the compiler must be
            # overridden on the make command line (no c++/g++ on OHOS CI).
            self.run(f"make -C src -j1 CXX={shlex.quote(cxx)} CXXFLAGS=-O2")

    def package(self):
        copy(self, "cba", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "licence.txt", self.source_folder,
             os.path.join(self.package_folder, "share", "licenses", "cba"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
