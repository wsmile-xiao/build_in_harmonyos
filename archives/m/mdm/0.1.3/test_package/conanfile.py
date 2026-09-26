#!/usr/bin/env python3
"""Conan test_package for mdm 0.1.3 — HarmonyOS consumer test via test.sh.

Upstream ships no test suite (MANIFEST.yml / reports/upstream-test-scan.txt);
test.sh executes the packaged mdm-run/mdm-master/mdm-slave binaries.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class MdmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        if not can_run(self):
            self.output.warning(
                "mdm test_package not executed: cannot run target binaries")
            return

        dep = self.dependencies.get("mdm")
        bin_dir = "bin"
        if dep is not None:
            try:
                rel = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
            except Exception:
                rel = "bin"
            if not os.path.isabs(rel):
                rel = os.path.join(dep.package_folder, rel)
            bin_dir = rel if os.path.isdir(rel) else os.path.join(
                dep.package_folder, "bin")
            self.output.info("mdm package_folder=%s bindir=%s" % (
                dep.package_folder, bin_dir))

        home = os.path.expanduser("~")
        rejected = (home, "/", "/tmp", "")
        tmpdir = ""
        for var in ("TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(var) or ""
            if cand in rejected or not os.path.isdir(cand):
                continue
            cand = os.path.join(cand, "mdm-test-%d" % os.getpid())
            try:
                os.makedirs(cand, exist_ok=True)
                tmpdir = cand
                break
            except OSError:
                continue
        if not tmpdir:
            tmpdir = os.path.join(home, "tmp", "mdm-scratch-%d" % os.getpid())
            os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP", "TEMPDIR"):
            os.environ[var] = tmpdir
        self.output.info("test TMPDIR=%s" % tmpdir)

        script = os.path.join(os.path.dirname(__file__), "test.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        self.run('"%s" "%s" "%s"' % (shell, script, bin_dir), env="conanrun")
