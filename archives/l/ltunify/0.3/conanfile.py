#!/usr/bin/env python3
"""Conan recipe - ltunify 0.3 (bare upstream Makefile, no configure script)."""
import os
import stat

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout


class LtunifyConan(ConanFile):
    name = "ltunify"
    version = "0.3"
    description = ("Command line tool to inspect and pair Logitech Unifying "
                   "receivers through /dev/hidraw*")
    license = "GPL-3.0-or-later"
    homepage = "https://lekensteyn.nl/logitech-unifying.html"
    url = ""  # CI fills this
    topics = ("logitech", "unifying", "hidraw", "usb", "receiver")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler comes from Conan conf, never from a bare shell ${CC}.
        comp = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict)
        cc = comp.get("c") or "clang"
        # Upstream Makefile has no ./configure and never assigns CC, so
        # $(CC) falls back to GNU make's built-in default "cc" - an alias
        # that does not exist on HarmonyOS (make: cc: No such file or
        # directory / Error 127). Injecting it on the make command line is
        # enough: it outranks both the built-in default and the environment.
        #
        # PACKAGE_VERSION is derived from `git describe`, which is empty in a
        # release tarball (no .git). Upstream Makefile line 13 reads
        # `ifeq (PACKAGE_VERSION, "")` - the `$(...)` is missing, so the test
        # compares the literal word and always takes the else branch,
        # yielding -DPACKAGE_VERSION="" and a blank `ltunify --version`.
        # Passing the version on the command line fixes it with zero patches.
        # Upstream CFLAGS (`?=`) are kept as-is: they carry -D_FORTIFY_SOURCE=2
        # and the stack protector, and were measured to compile clean with
        # clang 15.0.4 on the build host, so R1 parameter minimisation says do
        # not touch them.
        self.run("make -C %s CC=%s PACKAGE_VERSION=%s -j1"
                 % (self.source_folder, cc, self.version))

    def package(self):
        # Upstream hard-codes `install` as a *literal* command in three recipes
        # (Makefile lines 34/38 use `install -m755 -D`, line 41 uses
        # `install -m644 -D`) and defines no INSTALL make-variable, so there is
        # nothing to override from the make command line. On top of that, the
        # build environment's PATH does not contain /bin (measured: 8 PATH
        # entries, none of them /bin), hence `command -v install` is empty
        # (rc=1) and a bare `install` under sh dies with rc=127 -> `make
        # install` fails with "install: No such file or directory".
        # Measured on the same host: /bin/install *does* exist and *is*
        # executable (toybox 0.8.12, mode 0100755, 546360 bytes; a real
        # `/bin/install -m755 src dst` run returned rc=0), so the root cause is
        # a PATH lookup failure, not a missing command. Either way `make
        # install` cannot be reused as-is (E098 / E108): copy the artefacts
        # directly and set the mode that `install -m755` would have set.
        bindir = os.path.join(self.package_folder, "bin")
        for prog in ("ltunify", "read-dev-usbmon"):
            src = os.path.join(bindir, prog)
            copy(self, prog, self.source_folder, bindir)
            os.chmod(src, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP |
                     stat.S_IROTH | stat.S_IXOTH)
        # The udev rule grants non-root access to the receiver. It is a
        # system-level runtime policy, not something a Conan package may drop
        # into /etc, so it is shipped as package data for the integrator.
        copy(self, "42-logitech-unify-permissions.rules",
             os.path.join(self.source_folder, "udev"),
             os.path.join(self.package_folder, "res", "udev", "rules.d"))
        docdir = os.path.join(self.package_folder, "res", "doc", "ltunify")
        for doc in ("README.txt", "NEWS", "notes.txt"):
            copy(self, doc, self.source_folder, docdir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
