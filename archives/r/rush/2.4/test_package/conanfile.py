#!/usr/bin/env python3
"""Conan test_package for GNU Rush 2.4 - HarmonyOS functional consumer test.

The actual assertions live in test_package/test.sh (6 functional cases:
version banner, scanner tokenization, operator recognition, quoting,
superuser-only security gate, auxiliary tool load).  This conanfile only
resolves the packaged bindir and drives test.sh through self.run() so the
whole consumer test executes inside the conanrun environment (R34: no
subprocess).
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class RushTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv injects bin/ of run deps into PATH.
        # rush is an application package; without run=True the isolated CI
        # env would not expose the packaged binaries.
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        if not can_run(self):
            self.output.warning(
                "can_run() is False - skipping rush functional consumer test")
            return
        dep = self.dependencies["rush"]
        bin_dir = ""
        try:
            rel = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
        except Exception:
            rel = "bin"
        cand = rel if os.path.isabs(rel) else os.path.join(
            dep.package_folder, rel)
        bin_dir = cand if os.path.isdir(cand) else os.path.join(
            dep.package_folder, "bin")
        self.output.info("rush package_folder=%s bindir=%s" % (
            dep.package_folder, bin_dir))
        try:
            for fn in sorted(os.listdir(bin_dir)):
                fp = os.path.join(bin_dir, fn)
                self.output.info("rush bindir entry: %s link=%s exec=%s" % (
                    fn, os.path.islink(fp), os.access(fp, os.X_OK)))
        except OSError as e:
            self.output.warning("list rush bindir failed: %s" % e)
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
