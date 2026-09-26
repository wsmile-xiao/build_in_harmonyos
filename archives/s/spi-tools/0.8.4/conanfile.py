#!/usr/bin/env python3
"""Conan recipe for spi-tools 0.8.4 - command line tools for Linux spidev devices.

spi-config queries/sets the SPI controller configuration (mode, lsb, bits per
word, speed, spirdy) through SPI_IOC_* ioctls; spi-pipe does a full-duplex
transfer over the same character device. Two C programs, no third-party
library dependency at all (only libc + the Linux UAPI headers).

Key adaptation decisions (device-verified, see notes.md):
- the official GitHub tag archive contains only configure.ac/Makefile.am, no
  pre-generated configure/aclocal.m4/Makefile.in, so build() bootstraps with
  `autoreconf -fi`. The HNP image on HarmonyOS PC ships autoconf 2.72, perl,
  m4 and make but has **no automake/aclocal**, hence automake comes in as a
  tool_requires resolved with the build profile (same split as aribb24/1.0.4
  and argp-standalone/1.4.1 - autoconf itself is deliberately NOT
  tool_required: a conan-packaged autoconf pulls a perl whose Cwd.so is not
  executable on HMDFS, see comptty/1.0.3 notes);
- configure.ac has no AC_CANONICAL_HOST/AC_CONFIG_SUBDIRS, so no config.sub
  triple check happens: neither --build nor --host is needed (this is why the
  package avoids the E122/E072 family that blocked jaula);
- configure is launched with CONFIG_SHELL and SHELL set to /bin/sh (see
  _configure_with_binsh) because the shared OHOS profile exports hnp bash as
  the shell and that shell cannot getcwd() in the conan cache dirs (E386);
- package() copies the two linked binaries and the man pages by hand instead
  of running `make install`: on HMDFS `install -c` fails with Error 64
  (E182/E188 family, cf. aribb24's install shim). Static copying also keeps
  the autoconf-generated aux scripts out of the package;
- static-only by nature (a program has no shared flavor), so no shared/fPIC
  options are declared.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import load_toolchain_args
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SpiToolsConan(ConanFile):
    name = "spi-tools"
    version = "0.8.4"
    description = ("Command line tools to configure and drive Linux spidev "
                   "character devices: spi-config (SPI mode/speed/bits query "
                   "and setup) and spi-pipe (full-duplex transfer)")
    license = "GPL-2.0-only"
    homepage = "https://github.com/cpb-/spi-tools"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # Upstream's own build instructions are "autoreconf -fim": the tag
        # archive has no autotools output committed. automake/aclocal are the
        # only missing pieces on the build host (HNP has autoconf 2.72, perl,
        # m4), and libtool is not used by configure.ac at all.
        self.tool_requires("automake/1.18")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _patch_generated_configure(self):
        """Relax the two HMDFS-hostile spots in the autoreconf output.

        E011/E114: config.status creates its temp dir under `umask 077`; HMDFS
        maps the resulting 0700+setgid dir to file_manager so the building
        process cannot write into it and config.status silently produces no
        Makefile/config.h.
        E386: the autoconf >= 2.70 re-exec check uses `pwd`, which fails in
        some HMDFS cwd states even though $PWD is valid -> fall back to $PWD.
        Both are applied after autoreconf, since bootstrapping regenerates
        configure from scratch.
        """
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            return
        with open(configure, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        original = text
        text = text.replace("umask 077", "umask 022")
        needle = 'ac_pwd=`pwd` && test -n "$ac_pwd" &&'
        if needle in text:
            text = text.replace(
                needle,
                'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"\ntest -n "$ac_pwd" &&',
                1,
            )
        if text != original:
            with open(configure, "w", encoding="utf-8") as handle:
                handle.write(text)

    def _configure_with_binsh(self):
        """Run configure with the shell routed back to /bin/sh (E386).

        The framework profile ci/conan/profiles/ohos-aarch64 pins
        [buildenv] CONFIG_SHELL=SHELL=/data/service/hnp/bin/bash, and autoconf's
        prologue re-execs itself through $CONFIG_SHELL
        (`exec $CONFIG_SHELL $as_opts "$as_myself"`). hnp bash cannot even `pwd`
        inside the conan cache dirs on HMDFS (device measurement in that very
        directory: hnp bash -> rc=1 with "shell-init: error retrieving current
        directory: getcwd", /bin/sh -> rc=0), so configure aborts with
        "working directory cannot be determined".
        Single-factor control on device, same VPATH dir, only those two
        variables changed: hnp bash fails, /bin/sh configures cleanly.
        The argument list is still taken from AutotoolsToolchain's
        conanbuild.conf, so --prefix/--bindir handling is unchanged.
        """
        configure = os.path.join(self.source_folder, "configure")
        args = load_toolchain_args(self.generators_folder).get("configure_args", "") or ""
        self.run('env CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh "{}" {}'.format(
            configure, args))

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.autoreconf(args=["-fi"])
        self._patch_generated_configure()
        self._configure_with_binsh()
        # HMDFS has no mkfifo, so the make jobserver is unavailable (-j>1 breaks).
        autotools.make(args=["-j1"])

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        built = os.path.join(self.build_folder, "src")
        for program in ("spi-config", "spi-pipe"):
            copy(self, program, src=built, dst=bindir, keep_path=False)
            if not os.path.isfile(os.path.join(bindir, program)):
                raise ConanException(
                    "spi-tools package() found no built binary %r under %s"
                    % (program, built))
        # man pages are dist_man_MANS, i.e. committed static files.
        copy(self, "*.1", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # R38: application package, the software-level commands.json declares
        # the two tools; only bindirs matter for consumers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
