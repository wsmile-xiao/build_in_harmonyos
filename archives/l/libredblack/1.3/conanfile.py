#!/usr/bin/env python3
"""Conan recipe — libredblack 1.3 (red-black balanced tree library).

libredblack is Damian Ivereigh's C implementation of the red-black balanced
tree, packaged with a small API (init / search / find / delete / lookup / walk /
destroy) and a generator script that can emit a customised, name-mangled copy
of the whole library.

Build system : autotools.  The tarball ships a generated ``configure``,
``Makefile.in`` and ``config.h.in``, so no autoreconf is needed.
Package form : a library — ``lib/libredblack.a`` (or ``libredblack.so*`` with
               ``-o shared=True``), ``include/redblack.h`` and the man pages.
               No executables are installed, so no commands.json is required.

Configured with ``--without-rbgen``: ``rbgen`` is a Python script that
generates ``example4.c`` from ``example4.rb``, and it is Python-2 era (it dies
with ``TabError: inconsistent use of tabs and spaces in indentation`` under
Python 3).  Upstream's Makefile has an explicit fallback for its absence
("Create a dummy example4.c in case rbgen isn't present"), so disabling it
gives a clean, dependency-free build while the library and all other examples
still build.

OHOS adaptation — four portability patches, see conandata.yml:

  1. ``config.guess`` — the shipped script is the **2001-09-04** release: it has
     no HarmonyOS case, and its only ARM entry is ``arm*:Linux:*:*``, a pattern
     that does **not** match the string ``aarch64``.
  2. ``config.sub`` — must accept the ``linux-ohos`` kernel-os combination.  The
     KERNEL-OS special case next to ``linux-gnu*`` matters most: without it
     ``aarch64-unknown-linux-ohos`` is split into machine
     ``aarch64-unknown-linux`` (rejected, it has two dashes) plus os ``-ohos``.
  3. ``configure`` — its private temporary directories are created with
     ``umask 077``, which is unusable on the OHOS HMDFS.
  4. ``Makefile.in`` / ``Makefile.am`` — upstream hard-codes ``CFLAGS=-Wall``,
     which silently discards every flag the Conan toolchain exports; the
     compile line came out as plain ``-Wall`` with neither ``-O2`` nor
     ``-fPIC``.

Upstream tests: none.  ``Makefile.am`` has no ``TESTS`` and no
``check_PROGRAMS``; the ``example*`` programs are demonstration programs, not
tests (they assert nothing and have no expected output).  See
test_package/MANIFEST.yml.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibredblackConan(ConanFile):
    name = "libredblack"
    version = "1.3"
    description = ("libredblack — red-black balanced tree searching and "
                   "sorting library")
    license = "LGPL-2.1-only"
    homepage = "http://libredblack.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libredblack is prepared for Linux/OHOS targets only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # rbgen is a Python-2 era generator script; upstream provides a fallback
        # for its absence, and nothing in the library depends on it.
        tc.configure_args.append("--without-rbgen")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Standard autotools flow: Autotools.configure() invokes
        # "<source>/configure" from the build folder, so the generated Makefile
        # lands there and make/install (which run in the build folder) find it.
        #
        # -j1 on purpose: other work shares the Harmony PC.
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["redblack"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "libredblack")
