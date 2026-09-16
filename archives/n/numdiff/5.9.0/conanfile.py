#!/usr/bin/env python3
"""Conan recipe for numdiff 5.9.0 (autotools command-line application).

numdiff compares putatively similar files line by line and field by field,
ignoring small numeric differences and/or different numeric formats.
It also ships the companion tool ``ndselect``.
Upstream (GNU Savannah, nongnu project): https://www.gnu.org/software/numdiff/

HarmonyOS PC (OHOS / aarch64) adaptation notes:
  1. E011 — HMDFS: the autoconf-generated ``configure``/``config.status``
     machinery builds its scratch directory with ``umask 077``.  On HMDFS the
     owned-by-remapped-UID 0700 directory is not writable by the build
     process, so config.status aborts with
     "cannot create ./confjKllBp/subs1.awk: Permission denied" (real log).
     -> patches/0001-configure.patch  (umask 077 -> umask 022)
  2. E027 / PSCAN-MUSL-005 — OHOS ships no libintl (gettext) development
     library and upstream NLS is enabled by default.  -> configure --disable-nls
  3. linesplit.c — ``ssplit()`` over-counts substrings when the delimiter
     string ends with a separator, leaving part of the allocated pointer
     vector uninitialized.  glibc malloc frequently hands back zeroed memory
     so the bug stays hidden, but on musl the garbage pointers make the later
     ``strchr()``/``strcmp()`` vector scans (is_char_in_vector,
     remove_duplicates_from_string_vector) crash with SIGSEGV.
     -> patches/0002-linesplit.c.patch  (malloc -> calloc)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NumdiffConan(ConanFile):
    name = "numdiff"
    version = "5.9.0"
    description = ("numdiff - compare files line by line and field by field, "
                   "ignoring small numeric differences and/or different number formats")
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/numdiff/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # The upstream tarball stores every entry as "./numdiff-5.9.0/...".
        # We deliberately do NOT pass strip_root=True here: Conan derives the
        # common root folder from the first archive member name, and for this
        # "./"-prefixed tarball that name is "." — so strip_root=True would
        # strip only the leading "./" and still leave a nested numdiff-5.9.0/
        # directory behind (verified: with strip_root=True, source_folder ends
        # up holding numdiff-5.9.0/).  Instead we extract normally and flatten
        # that single top-level directory ourselves, so that configure, the
        # conandata patches and Autotools all see the tree at source_folder
        # root.
        get(self, **self.conan_data["sources"])
        top = os.path.join(self.source_folder, "numdiff-5.9.0")
        for entry in os.listdir(top):
            os.rename(os.path.join(top, entry), os.path.join(self.source_folder, entry))
        os.rmdir(top)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E027 / PSCAN-MUSL-005: OHOS has no libintl -> disable gettext/NLS.
        tc.configure_args.append("--disable-nls")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # numdiff ships two command-line tools: numdiff and ndselect.
        self.cpp_info.bindirs = ["bin"]
