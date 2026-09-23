#!/usr/bin/env python3
"""Conan test_package for alive 2.0.3 - CLI smoke test via test.sh."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class AliveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv only injects bin/ of run deps into PATH.
        # alive is an application package; without run=True test.sh
        # cannot resolve `alive` via `command -v` in the isolated CI env.
        self.requires(self.tested_reference_str, run=True)
        # alive is a Guile script (#!/usr/bin/env guile): the interpreter
        # must also be on PATH at test time. guile is a library-type
        # package (run=False by default), so request it explicitly.
        self.requires("guile/2.2.7.1", run=True)

    def test(self):
        if can_run(self):
            # Resolve the tested bindir directly: do not rely solely on
            # PATH (preflight showed `command -v alive` failing even when
            # the package dir was on PATH). Pass it as argv to test.sh.
            # cpp_info.bindirs[0] is relative ("bin"); join onto the real
            # package_folder to get an absolute dir.
            alive_dep = self.dependencies.get("alive")
            bin_dir = ""
            if alive_dep is not None:
                try:
                    rel = alive_dep.cpp_info.bindirs[0] if alive_dep.cpp_info.bindirs else "bin"
                except Exception:
                    rel = "bin"
                cand = rel if os.path.isabs(rel) else os.path.join(
                    alive_dep.package_folder, rel)
                if os.path.isdir(cand):
                    bin_dir = cand
                else:
                    bin_dir = os.path.join(alive_dep.package_folder, "bin")
                self.output.info("alive package_folder=%s bindir=%s" % (
                    alive_dep.package_folder, bin_dir))
                try:
                    for fn in sorted(os.listdir(bin_dir)):
                        fp = os.path.join(bin_dir, fn)
                        self.output.info("alive bindir entry: %s link=%s exec=%s" % (
                            fn, os.path.islink(fp), os.access(fp, os.X_OK)))
                except OSError as e:
                    self.output.warning("list alive bindir failed: %s" % e)
            script = os.path.join(os.path.dirname(__file__), "test.sh")
            shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
            # OHOS /tmp is read-only (erofs). The shell creates temp files
            # for $(...) at startup, before test.sh can export TMPDIR, so
            # seed a writable TMPDIR in the parent process first. HMBS
            # injects TMPDIR/TMP/TEMP; fall back to build_folder/tmp.
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
            os.environ.setdefault("XDG_CACHE_HOME", tmpdir)
            os.environ["GUILE_AUTO_COMPILE"] = "0"
            self.run('"%s" "%s" "%s"' % (shell, script, bin_dir), env="conanrun")
