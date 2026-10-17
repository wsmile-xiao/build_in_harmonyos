#!/usr/bin/env python3
"""Conan recipe — malbolge 0.1.0 (single-file C CLI interpreter).

Malbolge is an esoteric programming language designed by Ben Olmstead in 1998
(named after the eighth circle of Dante's Inferno). This recipe builds the
official reference interpreter from the single upstream source file malbolge.c
(no release tarball, no Makefile, no build system — just one .c file).

The interpreter reads a .mal program file from argv[1] and executes it. It is
public-domain software (the source header explicitly places it in the public
domain).

Build system: none — upstream is a single malbolge.c compiled directly.
License: public domain (declared in source header + Homebrew formula)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download
from conan.tools.layout import basic_layout


class MalbolgeConan(ConanFile):
    name = "malbolge"
    version = "0.1.0"
    description = "Reference interpreter for the Malbolge esoteric programming language (Ben Olmstead, 1998)"
    license = "public_domain"
    homepage = "https://esoteric.sange.fi/orphaned/malbolge/"
    url = "https://esoteric.sange.fi/orphaned/malbolge/malbolge.c"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        # Official upstream: single malbolge.c file (no tarball published).
        # download() fetches it as a raw file (get()/unzip would fail on a .c).
        src = self.conan_data["sources"]
        download(self, url=src["url"], filename=src["filename"], sha256=src["sha256"])

    def build(self):
        # R33: resolve the C compiler dynamically — never bare shell env vars
        # or hardcoded paths. Prefer tools.build:compiler_executables from the
        # Conan conf, but verify the path actually exists; if the conf value is
        # absent or stale (points to an env where that toolchain isn't mounted),
        # fall back to a PATH lookup for "clang". This keeps resolution dynamic
        # (no hardcoded /data/service/hnp, /storage/Users, SDK version, Worker
        # path) while tolerating a profile that may outdate the live mount.
        cc = None
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        conf_cc = comp_execs.get("c")
        if conf_cc and os.path.isfile(conf_cc):
            cc = conf_cc
        if not cc:
            cc = shutil.which("clang")
        if not cc:
            raise ConanInvalidConfiguration(
                "No C compiler found: tools.build:compiler_executables is "
                "unset/stale and 'clang' is not on PATH")
        # Upstream has no Makefile: malbolge.c is a self-contained single file.
        # Compile directly with the resolved toolchain. No hardcoded cc/g++.
        # -O2 matches a release build; the program only needs libc.
        self.run(f'"{cc}" -O2 -o malbolge malbolge.c', cwd=self.source_folder)

    def package(self):
        # malbolge is a command-line interpreter: install the binary to bin/
        copy(self, "malbolge", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
