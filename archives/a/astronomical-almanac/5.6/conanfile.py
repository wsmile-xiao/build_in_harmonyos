#!/usr/bin/env python3
"""Conan recipe — astronomical-almanac 5.6

Astronomical Almanac calculations: planetary positions, solar/lunar
ephemeris, coordinate transformations, nutation, precession, refraction,
rise/set/transit times, and more.

Build system: plain Makefile (no configure script).
License: Public domain (U.S. Government work).
Dependencies: none (only uses standard C math library -lm).
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class AstronomicalAlmanacConan(ConanFile):
    name = "astronomical-almanac"
    version = "5.6"
    description = "Astronomical Almanac: planetary ephemeris and celestial calculations"
    license = "Public-Domain"
    homepage = "https://github.com/DouglasAllen/clib-astronomical-almanac-5.6"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        # Include local tarball if present (for offline builds)
        local_tarball = os.path.join(self.recipe_folder,
                                     "astronomical-almanac_5.6.orig.tar.gz")
        if os.path.isfile(local_tarball):
            from conan.tools.files import copy
            copy(self, "astronomical-almanac_5.6.orig.tar.gz",
                 src=self.recipe_folder, dst=self.export_sources_folder)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"astronomical-almanac supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # Try pre-exported local tarball first (for offline builds)
        local_tarball = os.path.join(self.source_folder,
                                     "astronomical-almanac_5.6.orig.tar.gz")
        if os.path.isfile(local_tarball):
            from conan.tools.files import unzip
            unzip(self, local_tarball, destination=self.source_folder,
                  strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: CC/CFLAGS come from env script, not shell variables.
        comp_execs = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict)
        if isinstance(comp_execs, str):
            comp_execs = json.loads(comp_execs)
        cc = comp_execs.get("c", "clang") if comp_execs else "clang"

        env = Environment()
        env.define("CC", cc)
        tmpdir = os.environ.get("TMPDIR",
                                os.path.join(os.path.expanduser("~"), "tmp-build"))
        env.define("TMPDIR", tmpdir)
        env.vars(self).save_script("aa_build_env")

    def build(self):
        apply_conandata_patches(self)
        # Build only aa (main program). conjunct and moonrise have duplicate
        # symbol issues in the original source that need more extensive fixes.
        self.run("make -j1 aa CC=\"$CC\"", env="aa_build_env",
                 cwd=self.source_folder)

    def package(self):
        # Install aa binary and data files
        bindir = os.path.join(self.package_folder, "usr", "local", "bin")
        datadir = os.path.join(self.package_folder, "usr", "local", "share",
                               "astronomical-almanac")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(datadir, exist_ok=True)
        from conan.tools.files import copy
        copy(self, "aa", src=self.source_folder, dst=bindir)
        for datafile in ("aa.ini", "star.cat", "messier.cat", "orbit.cat"):
            copy(self, datafile, src=self.source_folder, dst=datadir)

    def package_info(self):
        self.cpp_info.bindirs = [os.path.join("usr", "local", "bin")]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Make tools available in PATH for consumers
        bindir = os.path.join(self.package_folder, "usr", "local", "bin")
        self.runenv_info.prepend_path("PATH", bindir)
