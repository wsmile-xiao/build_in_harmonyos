#!/usr/bin/env python3
"""Conan test_package for ylva 1.7 — HarmonyOS consumer validation.

Two layers, both driven from test():

Layer 1 (always runs, host independent) — ohos_abi_check.py inspects the
    *packaged* binary instead of executing it:
      A1 ELF64 + e_machine == EM_AARCH64        HarmonyOS PC arm64 target
      A2 .interp == /lib/ld-musl-aarch64.so.1   OHOS musl loader
      A3 DT_NEEDED carries no libcrypto/libssl/libsqlite3/libqrcodegen
                                                R26: those are system-name
                                                libraries and are linked
                                                statically, nothing is added to
                                                the OHOS /lib
      A4 no DT_RPATH/DT_RUNPATH                 the packaged binary must
                                                resolve through OHOS system
                                                paths, not build-time paths
    It is pure Python ELF parsing with no external tool, so it also runs on the
    macOS dev box that merely simulates the OHOS worker: that host can
    cross-compile the package but cannot execute an aarch64-linux-ohos ELF, and
    it must still validate the artifact rather than pass silently.  It is also
    what makes the CI L1e destructive reverse check meaningful when
    cross-building — move bin/ away and this layer fails.

Layer 2 (can_run only) — functional_test.py drives 25 cases against the
    packaged binary on a real HarmonyOS host: 21 functional cases covering the
    documented CLI surface (F1-F21, including the interactive add and the
    encryption round trip on a real pty) plus 4 HarmonyOS specific runtime
    cases (H1-H4).  Upstream ships no test framework at all; see
    test_package/MANIFEST.yml for the audit and the counting method.
"""
import os
import re
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run

# F1-F21 functional + H1-H4 HarmonyOS specific runtime cases.
EXPECTED_FUNCTIONAL_CASES = 25


class YlvaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv only injects bin/ of run dependencies into
        # PATH, and ylva is an application package.
        self.requires(self.tested_reference_str, run=True)

    def _bindir(self):
        """Absolute bin/ of the tested package (do not rely on PATH alone)."""
        dep = self.dependencies.get("ylva")
        if dep is None:
            raise ConanException("ylva dependency missing from the graph")
        rel = "bin"
        try:
            if dep.cpp_info.bindirs:
                rel = dep.cpp_info.bindirs[0]
        except Exception:
            rel = "bin"
        cand = rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)
        self.output.info(
            "ylva package_folder=%s bindir=%s" % (dep.package_folder, cand))
        return cand

    def test(self):
        bin_dir = self._bindir()
        binary = os.path.join(bin_dir, "ylva")
        python = sys.executable or "python3"

        # ── Layer 1: HarmonyOS artifact/ABI checks (host independent) ──
        checker = os.path.join(self.recipe_folder, "ohos_abi_check.py")
        self.run('"%s" "%s" --binary "%s"' % (python, checker, binary))

        # ── Layer 2: on-device runtime suite ──
        if not can_run(self) or self._local_ohos_simulation():
            self.output.info(
                "cross-building: an aarch64-linux-ohos ELF cannot execute on "
                "this host, so the %d functional cases are skipped here and "
                "are exercised on the HarmonyOS CI worker; the artifact/ABI "
                "layer above did execute against the packaged binary"
                % EXPECTED_FUNCTIONAL_CASES)
            return

        runner = os.path.join(self.recipe_folder, "functional_test.py")
        log = os.path.join(self.build_folder, "functional-test.log")
        # Conan 2's self.run() does not return the output, so capture it to a
        # file and read it back (the log stays visible for CI triage even when
        # the suite fails — ignore_errors keeps the failure handling here).
        self.run('"%s" "%s" --bindir "%s" > "%s" 2>&1'
                 % (python, runner, bin_dir, log), ignore_errors=True)
        with open(log, encoding="utf-8", errors="replace") as fh:
            result = fh.read()
        self.output.info(result.strip()[-4000:])

        m = re.search(r"RESULT: passed=(\d+) failed=(\d+)", result)
        if not m:
            raise ConanException(
                "ylva: functional suite produced no RESULT summary line")
        passed, failed = int(m.group(1)), int(m.group(2))
        self.output.info("ylva functional suite: passed=%d failed=%d"
                         % (passed, failed))
        if failed:
            raise ConanException(
                "ylva: %d functional case(s) failed — see the log above" % failed)
        if passed != EXPECTED_FUNCTIONAL_CASES:
            raise ConanException(
                "ylva: expected %d functional cases, only %d ran"
                % (EXPECTED_FUNCTIONAL_CASES, passed))

    def _local_ohos_simulation(self):
        """True when the host only *simulates* OHOS settings (macOS dev box).

        `conan-verify --profile ohos-local` passes the same OHOS profile as
        both -pr:h and -pr:b, so can_run() reports True even though the host
        cannot execute an aarch64-linux-ohos ELF.  The local profile marks
        itself with user.build:flex_bison_native (precedent: libidl2 0.8.14,
        secpwgen 1.3); ci/conan/profiles/ohos-aarch64 does not set it, so the
        real HarmonyOS worker still runs the full on-device suite.
        """
        try:
            return bool(self.conf.get("user.build:flex_bison_native",
                                      default=False))
        except Exception:
            return False
