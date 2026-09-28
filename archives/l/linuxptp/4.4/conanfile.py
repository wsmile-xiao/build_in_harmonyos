#!/usr/bin/env python3
"""Conan recipe for linuxptp 4.4 — PTP (IEEE 1588) implementation.

Upstream: https://linuxptp.sourceforge.net/ (tarball from downloads.nwtime.org)
Build:    plain upstream Makefile, no configure step.  `make` produces nine
          executables: ptp4l pmc phc2sys phc_ctl ts2phc timemaster hwstamp_ctl
          nsm tz2alt.

Adapted for HarmonyOS PC (OHOS / aarch64, device-native compile).

OHOS adaptation, two environment facts — no source patches are needed:

  1. `CC` — the upstream Makefile hardcodes `CC = $(CROSS_COMPILE)gcc`, and gcc
     does not exist on OHOS (`gcc: inaccessible or not found`).  The compiler is
     therefore taken from the Conan conf, never from a bare shell variable (R33).

  2. Kernel headers — `incdefs.sh` looks for <linux/net_tstamp.h> etc. under
     `${KBUILD_OUTPUT}` (upstream's own documented cross-build hook).  Without
     it the script falls back to the non-existent host `/usr/include`, misses
     the sysroot headers and leaves HAVE_ONESTEP_SYNC/HAVE_ONESTEP_P2P undefined;
     `missing.h` then re-defines the HWTSTAMP_TX_ONESTEP_* enumerators that the
     sysroot's <linux/net_tstamp.h> already defines (E119).  Setting
     KBUILD_OUTPUT to the OHOS sysroot fixes the probe and also adds the
     `-I<sysroot>/usr/include` include path.

  3. `__MUSL__` — the OHOS sysroot's <sys/socket.h> guards `struct
     sockaddr_storage` with `#ifndef __MUSL__`, while <linux/socket.h> defines it
     unconditionally; any translation unit that pulls in both then fails with
     "redefinition of 'sockaddr_storage'" (E091).  The SDK's own compiler driver
     (aarch64-unknown-linux-ohos-clang) always predefines __MUSL__ to keep the
     pair consistent; plain clang does not, so the recipe defines it explicitly.

Upstream ships no test suite (no tests/ directory, no `check`/`test` target), so
this port contributes its own unit suite (tests/test_linuxptp_units.c) covering
the core algorithm APIs; it is compiled against the objects `make` produced and
executed inside build() (R51 path B).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get, apply_conandata_patches
from conan.tools.layout import basic_layout

# Upstream Makefile: PRG = ptp4l hwstamp_ctl nsm phc2sys phc_ctl pmc timemaster ts2phc tz2alt
PRG = ["ptp4l", "hwstamp_ctl", "nsm", "phc2sys", "phc_ctl", "pmc",
       "timemaster", "ts2phc", "tz2alt"]

# Objects required to link the supplementary unit suite.  These are the pure
# algorithm modules (filters, hash, leap seconds, time stamp processing) plus
# the logging/util helpers they call into; util.o in turn needs the clock and
# socket helpers (phc.o, sk.o).
UNIT_TEST_OBJS = ["filter.o", "mave.o", "mmedian.o", "hash.o", "lstab.o",
                  "tsproc.o", "print.o", "util.o", "phc.o", "sk.o"]


class LinuxptpConan(ConanFile):
    name = "linuxptp"
    version = "4.4"
    description = ("linuxptp — Precision Time Protocol (IEEE 1588) userspace: "
                   "ptp4l, pmc, phc2sys, phc_ctl, ts2phc, timemaster, "
                   "hwstamp_ctl, nsm, tz2alt")
    license = "GPL-2.0-or-later"
    homepage = "https://linuxptp.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # tests/ holds the supplementary unit suite (upstream has no tests at
        # all).  It is a source file, not a patch, so it is exported as such:
        # conan merges exported sources into the source folder before source().
        copy(self, "*", src=os.path.join(self.recipe_folder, "tests"),
             dst=os.path.join(self.export_sources_folder, "tests"))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ── toolchain discovery ──────────────────────────────────────────────

    def _cc(self):
        """C compiler from the Conan conf (R33)."""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        if compilers and compilers.get("c"):
            return compilers["c"]
        return "clang"

    def _sysroot(self):
        """OHOS sysroot, used as KBUILD_OUTPUT so incdefs.sh finds <linux/*.h>.

        Derived from the compiler location
        (<sdk>/ohos/native/llvm/bin/clang -> <sdk>/ohos/native/sysroot), with the
        installed SDK layout as a fallback.  A candidate is only accepted when it
        really carries the kernel UAPI headers incdefs.sh probes for.
        """
        candidates = []
        real = os.path.realpath(self._cc())
        # <native>/llvm/bin/clang -> <native>
        native = os.path.dirname(os.path.dirname(os.path.dirname(real)))
        candidates.append(os.path.join(native, "sysroot"))
        candidates += sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot"),
            reverse=True)
        for cand in candidates:
            if os.path.isfile(os.path.join(cand, "usr/include/linux/net_tstamp.h")):
                return cand
        return ""

    # ── build ────────────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)

        cc = self._cc()
        cflags = []
        env = ""
        if self.settings.os == "OHOS":
            # The sysroot and the __MUSL__ define are OHOS-specific: native
            # Linux resolves both from its own host headers/toolchain.
            sysroot = self._sysroot()
            if not sysroot:
                raise ConanInvalidConfiguration(
                    "OHOS sysroot not found (expected "
                    "<sysroot>/usr/include/linux/net_tstamp.h)")
            env = 'KBUILD_OUTPUT="%s" ' % sysroot
            # E091: keep <sys/socket.h> and <linux/socket.h> consistent.
            cflags.append("-D__MUSL__")

        extra = " ".join(cflags)
        # R9: single job.  The Makefile has no `check`/`test` target, so the
        # upstream test step is the port's own suite (see _run_unit_tests).
        self.run('%smake -j1 CC="%s" EXTRA_CFLAGS="%s"'
                 % (env, cc, extra), cwd=self.source_folder)
        self._run_unit_tests(cc, extra)

    def _run_unit_tests(self, cc, extra):
        """Compile and run the supplementary unit suite (R51 path B).

        linuxptp 4.4 ships no tests: `find . -iname '*test*'` is empty and
        `make -n check` has no rule.  The suite therefore lives in this recipe
        (tests/test_linuxptp_units.c) and is linked against the objects built by
        the upstream Makefile, exercising deterministic inputs of the core
        algorithm APIs (filters, hash table, leap seconds, tsproc).
        """
        test_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(test_dir):
            raise ConanInvalidConfiguration(
                "supplementary tests/ directory missing from the source folder")
        objs = [o for o in UNIT_TEST_OBJS
                if os.path.isfile(os.path.join(self.source_folder, o))]
        missing = [o for o in UNIT_TEST_OBJS if o not in objs]
        if missing:
            raise ConanInvalidConfiguration(
                "unit test objects not built by make: %s" % ", ".join(missing))

        test_bin = os.path.join(self.build_folder, "linuxptp_units")
        cflags = "-Wall -D_GNU_SOURCE -DVER=4.4 %s" % extra
        self.run('%s -I"%s" "%s" %s -lm -lrt -pthread -o "%s"'
                 % (cc, self.source_folder,
                    os.path.join(test_dir, "test_linuxptp_units.c"),
                    " ".join(objs), test_bin),
                 cwd=self.source_folder)
        self.run('"%s"' % test_bin, cwd=self.source_folder)

    # ── package ──────────────────────────────────────────────────────────

    def package(self):
        # `make install` needs install(1), which OHOS does not ship
        # (`command -v install` -> not found), so the binaries are copied here.
        bin_dir = os.path.join(self.package_folder, "bin")
        for prg in PRG:
            copy(self, prg, self.source_folder, bin_dir, keep_path=False)
            installed = os.path.join(bin_dir, prg)
            if os.path.isfile(installed):
                os.chmod(installed, 0o755)
        # Upstream man pages travel with the release tarball; ship them when
        # present (make install would place them in <prefix>/man/man8).
        for prg in PRG:
            copy(self, "%s.8" % prg, self.source_folder,
                 os.path.join(self.package_folder, "man", "man8"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
