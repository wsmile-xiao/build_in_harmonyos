#!/usr/bin/env python3
"""Conan test_package for lm4tools 0.1.3 - HarmonyOS consumer validation.

Two layers, both driven from test():

Layer 1 (runs whenever the target is OHOS) - ohos_abi_check.py inspects the
    packaged artifact instead of executing it: A1-A9 cover ELF64/AArch64, the
    OHOS musl interpreter, .note.ohos.ident, musl + libusb DT_NEEDED, libusb
    imports UND in .dynsym, no host RPATH/RUNPATH, NX/PIE/RELRO/BIND_NOW and
    the absence of glibc symbol versioning.  It is pure Python ELF parsing
    with no external tool, so it also runs on hosts that cross-compile the
    package but cannot execute an aarch64-linux-ohos ELF.

Layer 2 (can_run only) - test_lm4tools.sh drives the safe, device-free CLI
    cases against the packaged binaries on a real HarmonyOS host: -V/-h/
    usage-error exits for lm4flash, and the no-device behaviour of both
    binaries.  lm4flash's flashing/verify paths and lmicdi's debug session
    require a physical Stellaris LaunchPad (USB 1cbe:00fd); those are
    explicitly out of scope here and never faked.
"""

import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run


class Lm4ToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lm4tools test supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # run=True: VirtualRunEnv only injects bin/ (and LD_LIBRARY_PATH for
        # libusb) of run dependencies, and lm4tools is an application package.
        self.requires(self.tested_reference_str, run=True)

    def _bindir(self):
        """Absolute bin/ of the tested package (do not rely on PATH alone)."""
        dep = self.dependencies.get("lm4tools")
        if dep is None:
            raise ConanException("lm4tools dependency missing from the graph")
        rel = "bin"
        try:
            if dep.cpp_info.bindirs:
                rel = dep.cpp_info.bindirs[0]
        except Exception:
            rel = "bin"
        cand = rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)
        self.output.info("lm4tools package_folder=%s bindir=%s"
                         % (dep.package_folder, cand))
        for tool in ("lm4flash", "lmicdi"):
            if not os.path.isfile(os.path.join(cand, tool)):
                raise ConanException(
                    f"lm4tools executable not found in the package: {cand}/{tool}")
        return cand

    def test(self):
        bin_dir = self._bindir()

        # Layer 1: HarmonyOS artifact/ABI checks (host independent).
        if str(self.settings.os) == "OHOS":
            checker = os.path.join(self.recipe_folder, "ohos_abi_check.py")
            for tool in ("lm4flash", "lmicdi"):
                binary = os.path.join(bin_dir, tool)
                self.run(" ".join(shlex.quote(arg) for arg in (
                    sys.executable, checker, "--binary", binary)))

        # Layer 2: on-device functional suite (device-free CLI surface only).
        if not can_run(self):
            self.output.info(
                "cross-building: an aarch64-linux-ohos ELF cannot execute on "
                "this host, so the test_lm4tools.sh runtime cases are skipped "
                "here and are exercised on the HarmonyOS CI worker; the "
                "artifact/ABI layer above did execute against the packaged "
                "binaries")
            return

        script = os.path.join(self.recipe_folder, "test_lm4tools.sh")
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
