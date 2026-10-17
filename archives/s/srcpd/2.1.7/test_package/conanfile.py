#!/usr/bin/env python3
"""Conan test_package — srcpd 2.1.7 daemon smoke verification.

Runs test.sh against the installed srcpd binary in the conanrun
environment (PATH holds the package sbin dir). All assertions invoke
the real daemon binary; no stub printing.
"""

import os

from conan import ConanFile


class SrcpdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        srcpd_dep = self.dependencies.get("srcpd")
        bin_dir = ""
        pkg_dir = ""
        if srcpd_dep is not None:
            pkg_dir = srcpd_dep.package_folder
            try:
                rel = srcpd_dep.cpp_info.bindirs[0] if srcpd_dep.cpp_info.bindirs else "bin"
            except Exception:
                rel = "bin"
            cand = rel if os.path.isabs(rel) else os.path.join(pkg_dir, rel)
            bin_dir = cand if os.path.isdir(cand) else os.path.join(pkg_dir, "bin")
            self.output.info("srcpd package_folder=%s bindir=%s" % (pkg_dir, bin_dir))
        script = os.path.join(os.path.dirname(__file__), "test.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP") or "")
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        self.run('"%s" "%s" "%s" "%s"' % (shell, script, bin_dir, pkg_dir), env="conanrun")
