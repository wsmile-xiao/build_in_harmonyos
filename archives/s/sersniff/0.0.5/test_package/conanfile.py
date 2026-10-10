#!/usr/bin/env python3
"""Conan test_package for sersniff 0.0.5 — CLI smoke test via test.sh.

sersniff is a serial/TCP sniffer CLI application (no library API). The
consumer test executes the installed `sersniff` binary and verifies real
CLI behaviour (version banner + usage help + baud validation). It emits
HMBS machine-evidence markers for the hard gate.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class SersniffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True so VirtualRunEnv injects sersniff's bin/ into PATH and
        # test.sh can resolve the binary.
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        if can_run(self):
            # Resolve the tested bindir directly from the package instead of
            # relying solely on PATH (more robust in the isolated CI env).
            dep = self.dependencies.get("sersniff")
            bin_dir = ""
            if dep is not None:
                try:
                    rel = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
                except Exception:
                    rel = "bin"
                cand = rel if os.path.isabs(rel) else os.path.join(
                    dep.package_folder, rel)
                if not os.path.isdir(cand):
                    cand = os.path.join(dep.package_folder, "bin")
                if os.path.isdir(cand):
                    bin_dir = cand
                self.output.info("sersniff package_folder=%s bindir=%s" % (
                    dep.package_folder, bin_dir))
            script = os.path.join(os.path.dirname(__file__), "test.sh")
            shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"

            # OHOS /tmp is read-only (erofs). Seed a writable TMPDIR in the
            # parent process so the shell's command substitution has a place
            # to write temp files before test.sh runs. HMBS injects
            # TMPDIR/TMP/TEMP; fall back to build_folder/tmp.
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
            self.run('"%s" "%s" "%s"' % (shell, script, bin_dir),
                     env="conanrun")
