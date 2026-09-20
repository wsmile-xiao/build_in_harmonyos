#!/usr/bin/env python3
"""Conan recipe — bus 3.1.11 (pure Makefile project).

bus is a daemonless local message broadcasting system (System V IPC based):
  - libbus (libbus.a / libbus.so): C library, public header bus.h
  - bus: command line utility (create/remove/listen/wait/broadcast/chmod/chown/chgrp)

Build system: plain POSIX Makefile + config.mk (no configure script).
The Makefile always builds libbus.a, libbus.so and the bus CLI together.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BusConan(ConanFile):
    name = "bus"
    version = "3.1.11"
    description = "bus — a simple daemonless system for broadcasting messages locally (C library + CLI)"
    license = "MIT"
    homepage = "https://github.com/maandree/bus"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"bus supports Linux/OHOS only, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler/flags must come from Conan conf, never bare shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # config.mk sets CC=c99 and CPPFLAGS with the required _DEFAULT_SOURCE etc.;
        # command-line vars override the makefile, so re-supply them here.
        cppflags = "-D_DEFAULT_SOURCE -D_BSD_SOURCE -D_XOPEN_SOURCE=700 -D_GNU_SOURCE"
        cflags = f"-Wall -Wextra -pedantic -O2 -fPIC {cppflags}"
        # LDFLAGS=-s -lrt from config.mk; keep -lrt (librt), drop -s for symbols
        self.run(f'make -j1 CC="{cc}" CFLAGS="{cflags}" LDFLAGS="-lrt"',
                 cwd=self.source_folder)

    def package(self):
        # The Makefile installs bin/lib/include + symlinks correctly (proven on
        # HMDFS). PREFIX= empty + DESTDIR=package_folder puts files at package root.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        self.run(f'make install DESTDIR="{self.package_folder}" PREFIX= MANPREFIX=/share/man CC="{cc}"',
                 cwd=self.source_folder)
        # Man pages are not needed for the conan package; keep only bin/lib/include/license.
        man_dir = os.path.join(self.package_folder, "share")
        if os.path.isdir(man_dir):
            import shutil
            shutil.rmtree(man_dir, ignore_errors=True)

    def package_info(self):
        # Library consumers link -lbus (libbus.a / libbus.so).
        self.cpp_info.libs = ["bus"]
        # bus CLI ships in bin/ (R38: commands.json declared at software level).
        self.cpp_info.bindirs = ["bin"]
