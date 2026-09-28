#!/usr/bin/env python3
"""Conan test_package for qemu 11.1.1 - HarmonyOS consumer smoke test via test.sh."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class QemuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv only injects bin/ of run deps into PATH.
        # qemu is an application package; without run=True test.sh cannot
        # resolve the packaged binaries in the isolated CI env.
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        if can_run(self):
            # Resolve the tested bindir directly: do not rely solely on PATH
            # (same rationale as vamps 0.99.2). cpp_info.bindirs[0] is
            # relative ("bin"); join onto the real package_folder for an
            # absolute dir.
            dep = self.dependencies.get("qemu")
            bin_dir = ""
            if dep is not None:
                try:
                    rel = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
                except Exception:
                    rel = "bin"
                cand = rel if os.path.isabs(rel) else os.path.join(
                    dep.package_folder, rel)
                bin_dir = cand if os.path.isdir(cand) else os.path.join(
                    dep.package_folder, "bin")
                self.output.info("qemu package_folder=%s bindir=%s" % (
                    dep.package_folder, bin_dir))
            script = os.path.join(os.path.dirname(__file__), "test.sh")
            shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
            # OHOS /tmp is read-only (erofs): seed a writable TMPDIR in the
            # parent process before exec (HMBS injects TMPDIR/TMP/TEMP; fall
            # back to build_folder/tmp).
            tmpdir = (
                os.environ.get("TMPDIR")
                or os.environ.get("TMP")
                or os.environ.get("TEMP")
                or ""
            )
            if not tmpdir or not os.path.isdir(tmpdir):
                tmpdir = os.path.join(self.build_folder, "tmp")
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except OSError:
                pass
            os.environ["TMPDIR"] = tmpdir
            os.environ["TMP"] = tmpdir
            os.environ["TEMP"] = tmpdir
            os.environ["TEMPDIR"] = tmpdir
            self.run('"%s" "%s" "%s"' % (shell, script, bin_dir), env="conanrun")
