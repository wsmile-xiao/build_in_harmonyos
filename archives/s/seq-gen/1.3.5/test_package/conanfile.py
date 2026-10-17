#!/usr/bin/env python3
"""Conan test_package for seq-gen 1.3.5 - HarmonyOS consumer validation.

Two layers, both driven from test():

Layer 1 (runs whenever the target is OHOS) - ohos_abi_check.py inspects the
    packaged artifact instead of executing it: A1-A9 cover ELF64/AArch64, the
    OHOS musl interpreter, .note.ohos.ident, musl-only DT_NEEDED, libm folded
    into libc, "not the tarball's prebuilt Mach-O", no host RPATH/RUNPATH,
    NX/PIE/RELRO/BIND_NOW and the absence of glibc symbol versioning.  It is
    pure Python ELF parsing with no external tool, so it also runs on the macOS
    dev box that cross-compiles the package but cannot execute an
    aarch64-linux-ohos ELF: that host must still validate the artifact rather
    than pass silently.  It is also what keeps the CI L1e destructive reverse
    check meaningful when cross-building - move bin/ away and this layer fails.

Layer 2 (can_run only) - test_seq_gen.sh drives 20 functional cases (F1-F20)
    against the packaged binary on a real HarmonyOS host: every documented CLI
    mode (HKY/WAG models, PHYLIP / relaxed PHYLIP / NEXUS / FASTA output,
    separate files, multiple datasets, gamma rate heterogeneity, multi-tree
    input, ancestral sequences) plus seed determinism and usage-error
    handling.  Upstream ships no test framework at all, so this is the
   补全 suite declared in MANIFEST.yml.
"""
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run


class SeqGenTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"seq-gen test supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # run=True: VirtualRunEnv only injects bin/ of run dependencies into
        # PATH, and seq-gen is an application package.
        self.requires(self.tested_reference_str, run=True)

    def _bindir(self):
        """Absolute bin/ of the tested package (do not rely on PATH alone)."""
        dep = self.dependencies.get("seq-gen")
        if dep is None:
            raise ConanException("seq-gen dependency missing from the graph")
        rel = "bin"
        try:
            if dep.cpp_info.bindirs:
                rel = dep.cpp_info.bindirs[0]
        except Exception:
            rel = "bin"
        cand = rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)
        self.output.info("seq-gen package_folder=%s bindir=%s"
                         % (dep.package_folder, cand))
        if not os.path.isfile(os.path.join(cand, "seq-gen")):
            raise ConanException(
                f"seq-gen executable not found in the package: {cand}/seq-gen")
        return cand

    def test(self):
        bin_dir = self._bindir()

        # Layer 1: HarmonyOS artifact/ABI checks (host independent).
        if str(self.settings.os) == "OHOS":
            checker = os.path.join(self.recipe_folder, "ohos_abi_check.py")
            binary = os.path.join(bin_dir, "seq-gen")
            self.run(" ".join(shlex.quote(arg) for arg in (
                sys.executable, checker, "--binary", binary)))
        else:
            self.output.info(
                "target os=%s: the A1-A9 artifact layer is OHOS specific and "
                "is skipped; the functional layer below still exercises the "
                "packaged binary" % self.settings.os)

        # Layer 2: on-device functional suite.
        if not can_run(self) or self._local_ohos_simulation():
            self.output.info(
                "cross-building: an aarch64-linux-ohos ELF cannot execute on "
                "this host, so the 20 test_seq_gen.sh runtime cases are "
                "skipped here and are exercised on the HarmonyOS CI worker; "
                "the artifact/ABI layer above did execute against the "
                "packaged binary")
            return

        script = os.path.join(self.recipe_folder, "test_seq_gen.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        # OHOS / is largely read-only (erofs): seed a writable TMPDIR in the
        # parent process before exec so the script's scratch files land there.
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
