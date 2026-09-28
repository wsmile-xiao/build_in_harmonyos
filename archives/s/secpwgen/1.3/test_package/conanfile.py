#!/usr/bin/env python3
"""Conan test_package for secpwgen 1.3 — HarmonyOS consumer validation.

Two layers, both driven from test():

Layer 1 (always runs) — ohos_abi_check.py inspects the packaged artifact
    instead of executing it:
      A1 ELF64 + e_machine == EM_AARCH64        HarmonyOS PC arm64 target
      A2 .interp == /lib/ld-musl-aarch64.so.1   OHOS musl loader, not glibc
      A3 DT_NEEDED carries no libcrypto/libssl  R26: openssl is a system-name
                                                library and is linked statically
    It is pure Python ELF parsing with no external tool, so it also runs on
    the macOS dev box that simulates the OHOS worker: that host can
    cross-compile the package but cannot execute an aarch64-linux-ohos ELF,
    and it must still validate the artifact rather than pass silently.  It is
    also what makes the CI L1e destructive reverse check meaningful when
    cross-building — move bin/ away and this layer fails.

Layer 2 (can_run only) — test.sh drives 13 cases against the packaged binary
    on a real HarmonyOS host: 10 functional cases covering every documented
    CLI mode (upstream ships no test framework at all) and 3 HarmonyOS
    specific runtime cases: the E051 uncatchable-SIGSYS privilege drop,
    secure-memory degradation inside the OHOS sandbox, and the kernel entropy
    source feeding RAND_bytes.
"""
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class SecpwgenTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv only injects bin/ of run dependencies into
        # PATH, and secpwgen is an application package.
        self.requires(self.tested_reference_str, run=True)

    def _bindir(self):
        """Absolute bin/ of the tested package (do not rely on PATH alone)."""
        dep = self.dependencies.get("secpwgen")
        if dep is None:
            raise ConanException("secpwgen dependency missing from the graph")
        rel = "bin"
        try:
            if dep.cpp_info.bindirs:
                rel = dep.cpp_info.bindirs[0]
        except Exception:
            rel = "bin"
        cand = rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)
        self.output.info(
            "secpwgen package_folder=%s bindir=%s" % (dep.package_folder, cand))
        return cand

    def test(self):
        bin_dir = self._bindir()

        # ── Layer 1: HarmonyOS artifact/ABI checks (host independent) ──
        checker = os.path.join(self.recipe_folder, "ohos_abi_check.py")
        binary = os.path.join(bin_dir, "secpwgen")
        self.run(" ".join(shlex.quote(arg) for arg in (
            sys.executable, checker, "--binary", binary)))

        # ── Layer 2: on-device runtime suite ──
        if not can_run(self) or self._local_ohos_simulation():
            self.output.info(
                "cross-building: an aarch64-linux-ohos ELF cannot execute on "
                "this host, so the 13 test.sh runtime cases are skipped here "
                "and are exercised on the HarmonyOS CI worker; the artifact/ABI "
                "layer above did execute against the packaged binary")
            return

        script = os.path.join(self.recipe_folder, "test.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        # OHOS /tmp is read-only (erofs): seed a writable TMPDIR in the parent
        # process before exec so test.sh and the binary both land there.
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP") or "")
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        for var in ("TMPDIR", "TMP", "TEMP", "TEMPDIR"):
            os.environ[var] = tmpdir
        self.run('"%s" "%s" "%s"' % (shell, script, bin_dir), env="conanrun")

    def _local_ohos_simulation(self):
        """True when the host only *simulates* OHOS settings (macOS dev box).

        `conan-verify --profile ohos-local` passes the same OHOS profile as
        both -pr:h and -pr:b, so can_run() reports True even though the host
        cannot execute an aarch64-linux-ohos ELF.  The local profile marks
        itself with user.build:flex_bison_native (precedent: libidl2 0.8.14);
        ci/conan/profiles/ohos-aarch64 does not set it, so the real HarmonyOS
        worker still runs the full on-device suite.
        """
        try:
            return bool(self.conf.get("user.build:flex_bison_native",
                                      default=False))
        except Exception:
            return False
