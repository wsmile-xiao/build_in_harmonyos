#!/usr/bin/env python3
"""Conan test_package for zcfan 1.4.0 — HarmonyOS consumer smoke test via test.sh.

zcfan is an application package: the only consumer-visible artifact is the
bin/zcfan CLI, so the L1 test runs the *packaged* binary (never a source-tree
build) and asserts its CLI contract on this OHOS target.  See
test_package/MANIFEST.yml for the upstream test audit and test_package/test.sh
for the individual cases.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class ZcfanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv only injects bin/ of run deps into PATH.
        # zcfan is an application package; without run=True test.sh cannot
        # resolve the packaged binary in the isolated CI env.
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        if not can_run(self):
            return

        # Resolve the tested bindir directly instead of relying on PATH
        # (same rationale as vamps 0.99.2 / alive 2.0.3): cpp_info.bindirs[0]
        # is documented relative ("bin"), so join it onto the real
        # package_folder to obtain an absolute directory.
        dep = self.dependencies.get("zcfan")
        bin_dir = ""
        if dep is not None:
            try:
                rel = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
            except Exception:
                rel = "bin"
            cand = rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)
            bin_dir = cand if os.path.isdir(cand) else os.path.join(dep.package_folder, "bin")
            self.output.info("zcfan package_folder=%s bindir=%s" % (dep.package_folder, bin_dir))
            try:
                for fn in sorted(os.listdir(bin_dir)):
                    fp = os.path.join(bin_dir, fn)
                    self.output.info(
                        "zcfan bindir entry: %s link=%s exec=%s"
                        % (fn, os.path.islink(fp), os.access(fp, os.X_OK))
                    )
            except OSError as e:
                self.output.warning("list zcfan bindir failed: %s" % e)

        script = os.path.join(os.path.dirname(__file__), "test.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        # OHOS /tmp is read-only (erofs): seed a writable TMPDIR in the parent
        # process before exec (HMBS injects TMPDIR/TMP/TEMP; fall back to
        # build_folder/tmp).
        tmpdir = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP") or ""
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        for var in ("TMPDIR", "TMP", "TEMP", "TEMPDIR"):
            os.environ[var] = tmpdir

        self.run('"%s" "%s" "%s"' % (shell, script, bin_dir), env="conanrun")
