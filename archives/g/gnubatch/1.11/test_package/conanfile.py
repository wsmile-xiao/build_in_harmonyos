#!/usr/bin/env python3
"""Conan test_package for gnubatch 1.11 - HarmonyOS functional consumer test.

The actual assertions live in test_package/test.sh (7 functional cases:
btpwchk version banner, gbch-hols version banner (curses front-end,
exercises the ncurses .so resolution), gbch-passwd password-file creation,
btpwchk correct-password roundtrip, wrong-password rejection, unknown-user
rejection, gbch-passwd usage error). This conanfile only resolves the
packaged directories (bin, libexec/gnubatch, sbin) and drives test.sh
through self.run() so the whole consumer test executes inside the
conanrun environment (R34: no subprocess).
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class GnubatchTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        if not can_run(self):
            self.output.warning("can_run() is False - skipping gnubatch functional consumer test")
            return
        dep = self.dependencies["gnubatch"]
        self.output.info("gnubatch package_folder=%s" % dep.package_folder)
        for rel in ("bin", "libexec/gnubatch", "sbin"):
            d = os.path.join(dep.package_folder, rel)
            if not os.path.isdir(d):
                self.output.warning("gnubatch packaged dir missing: %s" % d)
                continue
            try:
                for fn in sorted(os.listdir(d)):
                    fp = os.path.join(d, fn)
                    self.output.info("gnubatch %s entry: %s link=%s exec=%s" % (
                        rel, fn, os.path.islink(fp), os.access(fp, os.X_OK)))
            except OSError as e:
                self.output.warning("list %s failed: %s" % (d, e))
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
        # Device test fixture source (see pwshim.c): test.sh compiles it and
        # LD_PRELOADs it for cases 4-7 so gnubatch's password tools can
        # resolve the invoking uid (which is absent from /etc/passwd).
        os.environ["GNUBATCH_PWSHIM_SRC"] = os.path.join(
            os.path.dirname(__file__), "pwshim.c")
        self.run('"%s" "%s" "%s"' % (shell, script, dep.package_folder),
                 env="conanrun")
