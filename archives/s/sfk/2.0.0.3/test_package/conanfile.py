#!/usr/bin/env python3
"""Conan test_package for sfk 2.0.0.3 - consumer smoke test via test.sh."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class SfkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True so VirtualRunEnv injects the package bin/ dir onto PATH,
        # letting test.sh resolve `sfk` even in the isolated CI env.
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        if can_run(self):
            # Resolve the tested bindir directly (do not rely solely on
            # PATH), pass it as argv[1] to test.sh.
            sfk_dep = self.dependencies.get("sfk")
            bin_dir = ""
            if sfk_dep is not None:
                try:
                    rel = sfk_dep.cpp_info.bindirs[0] if sfk_dep.cpp_info.bindirs else "bin"
                except Exception:
                    rel = "bin"
                cand = rel if os.path.isabs(rel) else os.path.join(
                    sfk_dep.package_folder, rel)
                bin_dir = cand if os.path.isdir(cand) else os.path.join(
                    sfk_dep.package_folder, "bin")
            script = os.path.join(os.path.dirname(__file__), "test.sh")
            shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
            # OHOS /tmp may be read-only (erofs); seed a writable TMPDIR in
            # the parent process before test.sh creates temp files.
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
            # HarmonyOS-specific ABI check on the packaged binary (aarch64 ELF
            # + OHOS musl loader). Pure Python, no external tools.
            abi_py = os.path.join(self.recipe_folder, "ohos_abi_check.py")
            sfk_bin = os.path.join(bin_dir, "sfk")
            py = os.environ.get("HMBS_PYTHON3") or "python3"
            self.run('"%s" "%s" --binary "%s"' % (py, abi_py, sfk_bin),
                     env="conanrun")
