#!/usr/bin/env python3
"""Conan recipe for libpri 1.6.0 (upstream hand-written Makefile).

libpri is the Asterisk project's implementation of Primary Rate ISDN (PRI):
the Q.921 (LAPD) data-link layer, the Q.931 (layer 3) call-control layer and
the ROSE / QSIG / ETSI / DMS-100 / NI-2 supplementary-service facilities.
Upstream release: libpri 1.6.0 (2017-01-27), built by a plain root Makefile --
there is no `configure` and no autotools in the tarball.

HarmonyOS (OHOS aarch64) adaptation
-----------------------------------
* The recipe drives `make` directly and takes the compiler and archiver from
  the Conan conf (`tools.build:compiler_executables`, R33). The Makefile's
  `CC=gcc` default and its literal `ar`/`ranlib` calls are never relied upon:
  patch 0001 turns the archiver into `$(AR)`/`$(RANLIB)` variables.
* Upstream `UTILITIES` is `pridump pritest rosetest testprilib`. `pridump`
  and `pritest` include `<dahdi/user.h>` / `<dahdi/tonezone.h>` -- the DAHDI
  kernel-driver interface, which is Linux-only, absent from OHOS and not even
  shipped in the release tarball. They therefore cannot be built here; the
  recipe builds the two portable programs (`rosetest`, `testprilib`) and runs
  them as the upstream test evidence.
* Patch 0002 replaces the non-POSIX `<sys/signal.h>` include in
  `testprilib.c` with `<signal.h>`. The OHOS sysroot redirects the former
  with `#warning`, which upstream's `-Werror` promotes to a hard error.
* The Makefile runs `/sbin/ldconfig` right after linking the shared library.
  OHOS has no ldconfig, so the recipe passes `LDCONFIG=true`.
* Upstream `rosetest` always exits 0: it reports per-case failures through
  `pri_error()` and its `main()` unconditionally `return 0`. The recipe
  therefore validates its *output* (267 executed cases, zero failure markers)
  instead of trusting the exit code.

Upstream test inventory (see test_package/MANIFEST.yml for the full evidence)
----------------------------------------------------------------------------
* `rosetest`   -- 267 data-driven ROSE encode/decode round-trip cases

  = 143 ETSI + 112 QSIG + 4 DMS-100 + 2 NI-2 message arrays
    + 6 "unusually encoded message" decode cases.

* `testprilib` -- BRI point-to-multipoint loopback smoke test: two libpri
  stacks (PRI_NETWORK + PRI_CPE) joined by a `socketpair()`, driven for 5 s by
  two threads; the oracle is the protocol event trace it prints.
* `pritest`    -- NOT RUN: needs the DAHDI kernel driver and `<dahdi/*.h>`.
* `pridump`    -- diagnostic utility, not a test; also needs `<dahdi/user.h>`.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    save,
)
from conan.tools.layout import basic_layout

# Round-trip cases executed by `rosetest` (see the module docstring).
ROSETEST_CASES = 267

# Failure markers emitted by `rosetest`'s two reporting helpers. `pri_error`
# is also used for benign progress lines ("libpri version tested: ..."), so
# the scan is anchored on the exact failure formats rather than on `Error:`.
ROSETEST_FAILURE_PATTERNS = (
    re.compile(r"Error: Message:\d+ "),
    re.compile(r"Error: .* test: Message failed to decode"),
    re.compile(r"did not match"),
)

# Application-level lines that prove the `testprilib` loopback really moved
# Q.921/Q.931 frames in both directions: NETWORK side came up and sent a
# SETUP, CPE side received it as RING, and the NETWORK side received the
# CPE's ALERTING as RINGING. Byte-for-byte stable across runs (verified
# 3x, see reports/).
TESTPRILIB_REQUIRED_LINES = (
    "Network is up.  Sending blast of calls!",
    "Setup 1 calls!",
    "PRI 2: PRI_EVENT_RING (5)",
    "PRI 1: PRI_EVENT_RINGING (7)",
)


class LibpriConan(ConanFile):
    name = "libpri"
    version = "1.6.0"
    description = (
        "libpri -- Primary Rate ISDN (PRI) protocol library "
        "(Q.921 LAPD, Q.931 call control, ROSE/QSIG/ETSI supplementary services)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.asterisk.org/"
    url = "https://github.com/asterisk/libpri"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libpri targets POSIX systems (Linux/OHOS), got %s"
                % self.settings.os
            )

    def layout(self):
        # The Makefile is at the root of the extracted sources: keep the build
        # folder on them so `make` finds it (same idiom as libfilteraudio).
        basic_layout(self, build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # libc only: no third-party dependency, no published requirement.
        pass

    def build(self):
        apply_conandata_patches(self)

        cc, ar, ranlib = self._tools()
        # R9: never -j$(nproc) -- the upstream Makefile has no sub-makes, and
        # this is a shared device.
        # UTILITIES: only the two portable test programs (see module docstring).
        self.run(
            'make -j1 CC={} AR={} RANLIB={} LDCONFIG=true '
            'UTILITIES="rosetest testprilib"'.format(cc, ar, ranlib),
            cwd=self.source_folder,
        )
        self._run_upstream_tests()

    def _tools(self):
        """Compiler and archiver from the Conan conf (R33), never from the shell."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        # The OHOS profile only pins `c`/`cpp`; fall back to the LLVM archiver
        # of the same toolchain, then to the plain POSIX names.
        ar = compilers.get("ar") or shutil.which("llvm-ar") or "ar"
        ranlib = compilers.get("ranlib") or shutil.which("llvm-ranlib") or "ranlib"
        return cc, ar, ranlib

    def _run_upstream_tests(self):
        """Run the two portable upstream test programs; fail the build on a
        genuine upstream failure (evidence for the CI log)."""
        summary = {"programs": {}, "source": "libpri 1.6.0 release tarball"}

        # ---- rosetest: 267 ROSE encode/decode round-trip cases -------------
        rosetest_log = os.path.join(self.build_folder, "rosetest.log")
        self.run('./rosetest > "%s" 2>&1' % rosetest_log, cwd=self.source_folder)
        text = self._read(rosetest_log)
        executed = text.count("encoded length is")
        failures = [
            line
            for line in text.splitlines()
            if any(pattern.search(line) for pattern in ROSETEST_FAILURE_PATTERNS)
        ]
        summary["programs"]["rosetest"] = {
            "kind": "data-driven encode/decode round-trip",
            "cases_executed": executed,
            "cases_expected": ROSETEST_CASES,
            "failures": len(failures),
            "log": "rosetest.log",
        }
        self.output.info(
            "upstream rosetest: %d/%d cases executed, %d failure marker(s)"
            % (executed, ROSETEST_CASES, len(failures))
        )
        if executed != ROSETEST_CASES:
            raise ConanException(
                "rosetest: expected %d round-trip cases, found %d "
                "(upstream suite changed or cases aborted early; log: %s)"
                % (ROSETEST_CASES, executed, rosetest_log)
            )
        if failures:
            raise ConanException(
                "rosetest: %d failure marker(s), first: %s (full log: %s)"
                % (len(failures), failures[0].strip(), rosetest_log)
            )

        # ---- testprilib: BRI PTMP loopback smoke test ----------------------
        testprilib_log = os.path.join(self.build_folder, "testprilib.log")
        self.run(
            './testprilib > "%s" 2>&1' % testprilib_log, cwd=self.source_folder
        )
        text2 = self._read(testprilib_log)
        missing = [line for line in TESTPRILIB_REQUIRED_LINES if line not in text2]
        summary["programs"]["testprilib"] = {
            "kind": "BRI point-to-multipoint loopback over socketpair",
            "required_event_lines": list(TESTPRILIB_REQUIRED_LINES),
            "missing_event_lines": missing,
            "log": "testprilib.log",
        }
        self.output.info(
            "upstream testprilib: %d/%d required protocol event lines present"
            % (len(TESTPRILIB_REQUIRED_LINES) - len(missing),
               len(TESTPRILIB_REQUIRED_LINES))
        )
        if missing:
            raise ConanException(
                "testprilib: missing protocol event line(s) %s -- the loopback "
                "did not complete (full log: %s)" % (missing, testprilib_log)
            )

        summary["not_run"] = {
            "pritest": "requires the DAHDI kernel driver and <dahdi/*.h> "
                       "(Linux-only, absent from OHOS and from the tarball)",
        }
        save(
            self,
            os.path.join(self.build_folder, "upstream-test-result.json"),
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        )

    @staticmethod
    def _read(path):
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()

    def package(self):
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "libpri.h",
            self.source_folder,
            os.path.join(self.package_folder, "include"),
        )
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            # Upstream builds libpri.so.1.4 (SONAME 1.4) plus the libpri.so
            # development symlink; reproduce both, then drop the static archive
            # so the package does not mix ABIs.
            copy(self, "libpri.so.*", self.source_folder, libdir)
            os.symlink("libpri.so.1.4", os.path.join(libdir, "libpri.so"))
            rm(self, "libpri.a", libdir)
        else:
            copy(self, "libpri.a", self.source_folder, libdir)
            for name in ("libpri.so", "libpri.so.1.4"):
                rm(self, name, libdir)

    def package_info(self):
        self.cpp_info.libs = ["pri"]
        # The library itself only needs libc (`nm --undefined-only libpri.a`
        # resolves to libc symbols only); no libm/pthread requirement.
