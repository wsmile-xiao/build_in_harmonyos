#!/usr/bin/env python3
"""Conan test_package for qalc 5.11.0 — HarmonyOS consumer validation.

Two layers, both driven from test():

Layer 1 (always runs) — ohos_abi_check.py inspects the packaged artifacts
    instead of executing them:
      A1 ELF64 + e_machine == EM_AARCH64       HarmonyOS PC arm64 target
      A2 .interp == /lib/ld-musl-aarch64.so.1  OHOS musl loader, not glibc
      A3 DT_NEEDED has libqalculate.so, no libcurl/libicu
      A4 libqalculate.so references no pthread_cancel family symbol
    Pure-Python ELF parsing, no external tools, so it also runs on the macOS
    dev box that simulates the OHOS worker (that host cannot execute an
    aarch64-linux-ohos ELF but must still validate the artifact).  This also
    keeps the CI L1e destructive reverse check meaningful: move bin/ away and
    this layer fails.

Layer 2 (can_run only) — test.sh drives the packaged qalc on a real
    HarmonyOS host:
      * the complete upstream batch suite (17 files, 688 input->expected
        cases, executed by qalc's own `--test-file` runner, files copied
        verbatim from the release tarball)
      * 3 HarmonyOS-specific runtime checks: packaged definitions loading +
        unit conversion, plain expression evaluation exit codes, and a
        musl-libm trig evaluation
"""
import glob
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class QalcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv puts the package's bindir on PATH; the
        # runtime shared libs (gmp/mpfr/libxml2/readline) come from the
        # explicit deps below.
        self.requires(self.tested_reference_str, run=True)
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")
        self.requires("libxml2/2.15.3")
        self.requires("readline/8.3")

    def _package_dir(self):
        dep = self.dependencies.get("qalc")
        if dep is None:
            raise ConanException("qalc dependency missing from the graph")
        return dep.package_folder

    def _lib_dirs(self):
        """SDK + system + package + dependency lib dirs, ordering matters."""
        dirs = []
        sdk_cxx = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                   "ohos/native/llvm/lib/aarch64-linux-ohos")
        for d in (sdk_cxx, "/system/lib64", "/system/lib"):
            if os.path.isdir(d) and d not in dirs:
                dirs.append(d)
        pkg = self._package_dir()
        for d in (os.path.join(pkg, "lib"),):
            if os.path.isdir(d) and d not in dirs:
                dirs.append(d)
        for _ref, _dep in self.dependencies.items():
            for d in (_dep.cpp_info.libdirs or []):
                if os.path.isabs(d) and d not in dirs:
                    dirs.append(d)
        return dirs

    def test(self):
        pkg = self._package_dir()
        bin_dir = os.path.join(pkg, "bin")
        qalc = os.path.join(bin_dir, "qalc")
        if not os.path.isfile(qalc):
            raise ConanException("packaged qalc executable missing: %s" % qalc)
        libs = sorted(glob.glob(os.path.join(pkg, "lib", "libqalculate.so*")))
        if not libs:
            raise ConanException("packaged libqalculate.so missing in %s/lib"
                                 % pkg)

        # ── Layer 1: HarmonyOS artifact/ABI checks (host independent) ──
        checker = os.path.join(self.recipe_folder, "ohos_abi_check.py")
        self.run(" ".join(shlex.quote(arg) for arg in (
            sys.executable, checker, "--binary", qalc, "--lib", libs[0])))

        # ── Layer 2: on-device runtime suite ──
        if not can_run(self) or self._local_ohos_simulation():
            self.output.info(
                "cross-building: an aarch64-linux-ohos ELF cannot execute on "
                "this host, so the 688 upstream batch cases and the 3 runtime "
                "checks are skipped here and are exercised on the HarmonyOS "
                "CI worker; the artifact/ABI layer above did execute against "
                "the packaged binary and library")
            return

        script = os.path.join(self.recipe_folder, "test.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        datadir = os.path.join(pkg, "share", "qalculate")
        # Runtime loader path: SDK libc++ first (the binary needs the SDK's
        # newer libc++_shared.so), then the package lib dir, then conan deps.
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            self._lib_dirs() + [os.environ.get("LD_LIBRARY_PATH", "")]).rstrip(os.pathsep)
        os.environ["QALCULATE_DEFINITIONS_DIR"] = datadir
        self.output.info("LD_LIBRARY_PATH=%s" % os.environ["LD_LIBRARY_PATH"])
        self.output.info("QALCULATE_DEFINITIONS_DIR=%s" % datadir)
        # test.sh derives the tests/ dir from its own location.  qalc's
        # --test-file mode must be invoked with an ABSOLUTE file path:
        # stats.batch contains `load(tests/vectordata.csv)`, and OHOS qalc
        # resolves relative load() paths against the current directory, so
        # the script cd's into its own directory (next to tests/).
        self.run('cd "%s" && "%s" "%s" "%s" "%s"'
                 % (self.recipe_folder, shell, script, bin_dir, datadir),
                 env="conanrun")

    def _local_ohos_simulation(self):
        """True when the host only *simulates* OHOS settings (macOS dev box).

        `conan-verify --profile ohos-local` passes the same OHOS profile as
        both -pr:h and -pr:b, so can_run() reports True even though the host
        cannot execute an aarch64-linux-ohos ELF.  The local profile marks
        itself with user.build:flex_bison_native (precedent: libidl2 0.8.14,
        secpwgen 1.3); the CI profile does not, so the real HarmonyOS worker
        still runs the full on-device suite.
        """
        try:
            return bool(self.conf.get("user.build:flex_bison_native",
                                      default=False))
        except Exception:
            return False
