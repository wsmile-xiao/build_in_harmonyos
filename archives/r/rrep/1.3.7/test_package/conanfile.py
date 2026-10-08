#!/usr/bin/env python3
"""Conan test_package for rrep 1.3.7 - HarmonyOS functional consumer test.

The actual assertions live in test_package/test.sh (7 functional cases:
version banner, help output, fixed-string replace, regex replace,
dry-run, ignore-case, recursive). This conanfile only resolves the packaged
bindir and drives test.sh through self.run() so the whole consumer test
executes inside the conanrun environment (R34: no subprocess).
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class RrepTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        if not can_run(self):
            self.output.warning("can_run() is False - skipping rrep functional consumer test")
            return
        dep = self.dependencies["rrep"]
        try:
            rel = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
        except Exception:
            rel = "bin"
        cand = rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)
        bin_dir = cand if os.path.isdir(cand) else os.path.join(dep.package_folder, "bin")
        self.output.info("rrep package_folder=%s bindir=%s" % (dep.package_folder, bin_dir))
        try:
            for fn in sorted(os.listdir(bin_dir)):
                fp = os.path.join(bin_dir, fn)
                self.output.info("rrep bindir entry: %s link=%s exec=%s" % (
                    fn, os.path.islink(fp), os.access(fp, os.X_OK)))
        except OSError as e:
            self.output.warning("list rrep bindir failed: %s" % e)
        script = os.path.join(os.path.dirname(__file__), "test.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
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
