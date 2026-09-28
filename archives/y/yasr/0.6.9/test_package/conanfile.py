#!/usr/bin/env python3
"""Conan test_package for yasr 0.6.9 — HarmonyOS consumer smoke test via test.sh.

yasr ships no upstream test harness (see MANIFEST.yml), so these are new
HarmonyOS consumer cases that exercise the packaged OHOS binary itself: ELF
load, the packaged default configuration file, the man page, and both sides of
yasr's configuration lookup (`-C`), which is the only CLI surface yasr offers
— it has no --version/--help.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class YasrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv only injects run-dependency bin/ into PATH.
        # yasr is an application package; without run=True test.sh could not
        # resolve the packaged binary in the isolated CI env.
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        if can_run(self):
            # Resolve the tested package folders explicitly instead of relying
            # on PATH alone (same rationale as vamps 0.99.2 / alive 2.0.3):
            # cpp_info.bindirs is relative, so join it onto package_folder.
            dep = self.dependencies.get("yasr")
            bin_dir = ""
            pkg_dir = ""
            if dep is not None:
                pkg_dir = dep.package_folder or ""
                try:
                    rel = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
                except Exception:
                    rel = "bin"
                bin_dir = rel if os.path.isabs(rel) else os.path.join(pkg_dir, rel)
                if not os.path.isdir(bin_dir):
                    bin_dir = os.path.join(pkg_dir, "bin")
                self.output.info("yasr package_folder=%s bindir=%s" % (pkg_dir, bin_dir))
                try:
                    for fn in sorted(os.listdir(bin_dir)):
                        fp = os.path.join(bin_dir, fn)
                        self.output.info("yasr bindir entry: %s link=%s exec=%s" % (
                            fn, os.path.islink(fp), os.access(fp, os.X_OK)))
                except OSError as e:
                    self.output.warning("list yasr bindir failed: %s" % e)
            script = os.path.join(os.path.dirname(__file__), "test.sh")
            shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
            # OHOS /tmp is read-only (erofs): seed a writable TMPDIR before
            # exec (HMBS injects TMPDIR/TMP/TEMP; fall back to build/tmp).
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
            # HMDFS/HMBS note: chmod is ignored on this filesystem, so the
            # packaged binary's exec bit cannot be "fixed" here — the exec
            # probe in test.sh case 1 is therefore an assertion, not a repair.
            self.run('"%s" "%s" "%s" "%s"' % (shell, script, bin_dir, pkg_dir),
                     env="conanrun")
