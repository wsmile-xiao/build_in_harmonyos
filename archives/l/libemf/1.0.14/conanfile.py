#!/usr/bin/env python3
"""Conan recipe for libEMF 1.0.14 — Enhanced Metafile (EMF) generation library.

libEMF implements a POSIX/GCC-compatible subset of the ECMA-234 GDI so that
programs without a native GDI (Grace, gnuplot, ...) can emit Enhanced
Metafiles.  The package ships:

  * libEMF.so.1      — C++ implementation behind the C API declared in
                       include/libEMF/emf.h
  * include/libEMF/  — public headers (emf.h + the bundled wine/ GDI types)
  * bin/printemf     — metafile reader/editor tool (src/printemf.c), declared
                       in archives/l/libemf/commands.json (R38)

OHOS adaptations (patches/, modified files only):

  0001 config config.guess
      Teach config.guess the HarmonyOS uname (E007).  uname -s reports
      "HarmonyOS" on OHOS, which the upstream 2022 config.guess does not
      know, so configure dies with "unable to guess system type".
  0002 config config.sub
      Accept the aarch64-unknown-linux-ohos triplet (E072): the basic_os
      mapping, the OS whitelist and the kernel-OS whitelist all need the
      ohos entries — without the third one config.sub rejects a valid
      triplet with "Kernel `linux' not known to work with OS `ohos'".
  0003 configure
      Create the config.status temporary directory with umask 022 instead of
      umask 077 (E011/E129): HMDFS forces setgid on new directories, so a
      0700 temp dir is not writable even by its owner and config.status dies
      with "could not setup config files machinery".

Build notes:

  * configure must run with CONFIG_SHELL unset (E386): the CI profile sets
    CONFIG_SHELL to the hnp bash, autoconf's configure re-executes itself
    under any non-empty CONFIG_SHELL, and that bash fails its startup getcwd()
    on HMDFS build folders, so configure aborts with "working directory cannot
    be determined".  It has to be a POSIX unset, not an empty value: an empty
    CONFIG_SHELL is substituted into the Makefile and breaks make.
  * make runs single-threaded (-j1): the GNU make jobserver FIFO cannot be
    created on HMDFS (E074).
  * build() runs the upstream suite: tests/docheck[123].sh compare the
    generated EMFs byte-for-byte against the golden files in tests/emfs/,
    and the three upstream check_PROGRAMS that upstream never registers in
    TESTS (check4, example1, example2) are executed as well, so all six
    upstream test programs are exercised.  The L1 test_package then exercises
    the installed package from the consumer side (C API, artifact round-trip,
    packaged tool).
"""
import os

from conan import ConanFile
from conan.tools.build import load_toolchain_args
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibemfConan(ConanFile):
    name = "libemf"
    version = "1.0.14"
    description = "Library for generating Enhanced Metafiles (EMF) on POSIX systems"
    license = "LGPL-2.1-or-later"
    homepage = "https://sourceforge.net/projects/libemf/"
    url = "https://sourceforge.net/projects/libemf/files/libemf/1.0.14/libemf-1.0.14.tar.gz"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # libEMF is not a system library name on OHOS; ship the shared library and
    # let Conan manage the runtime dependency.
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # E386: keep the official configure arguments (they carry the Conan
        # prefix/bindir/libdir options) but run configure in a shell where
        # CONFIG_SHELL has been unset, so autoconf does not re-execute into
        # the hnp bash whose getcwd() fails on HMDFS build folders.
        toolchain_args = load_toolchain_args(self.generators_folder)
        self.run(f'unset CONFIG_SHELL; '
                 f'"{os.path.join(self.source_folder, "configure")}" '
                 f'{toolchain_args.get("configure_args")}',
                 cwd=self.build_folder, env="conanbuild")
        autotools.make(args=["-j1"])
        # Upstream suite: 3 registered shell tests comparing the generated
        # EMFs byte-exact against tests/emfs/*.emf.
        autotools.make(target="check", args=["-j1"])
        # `make check` also builds the remaining upstream check_PROGRAMS
        # (check4, example1, example2) that upstream never registers in TESTS.
        # Run them too so the whole upstream program inventory is exercised
        # (each writes its own metafile and returns 0; example2 replays a
        # metafile passed on the command line).
        self.run("./check4 && ./example1 && ./example2 example1.emf",
                 cwd=os.path.join(self.build_folder, "tests"), env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING.LIB", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["EMF"]
        self.cpp_info.bindirs = ["bin"]
