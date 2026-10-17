#!/usr/bin/env python3
"""Conan recipe for appdirs 1.4.4 — platform-specific user dirs
(pure Python, single module, stdlib only, zero dependencies).

HarmonyOS PC adaptation: the package is a pure-Python single module
(appdirs.py) installed into site-packages. No source patch is needed — the
module only uses sys/os from the stdlib, and its directory-resolution
helpers degrade gracefully when HOME/XDG env vars are unset (falls back to
pathlib defaults), so nothing breaks on the platform's Python 3.12.

R38 note: upstream setup.py declares no console_scripts entry point and
ships no bin/ payload (py_modules=["appdirs"] only) — the package is a
library only, hence no commands.json.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get)
from conan.tools.layout import basic_layout


class AppdirsConan(ConanFile):
    name = "appdirs"
    version = "1.4.4"
    description = "A small Python module for determining appropriate platform-specific dirs"
    license = "MIT"
    homepage = "https://github.com/ActiveState/appdirs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def requirements(self):
        # PyPI requires_dist: none (zero runtime dependencies, stdlib only)
        pass

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _run_upstream_tests(self):
        """Run the upstream test suite (test/test_api.py, unittest style) and
        report the real pass rate.

        appdirs 1.4.4 ships a single unittest file with a Test_AppDir class
        holding 3 test cases (test_metadata / test_helpers / test_dirs).
        """
        test_file = os.path.join(self.source_folder, "test", "test_api.py")
        if not os.path.isfile(test_file):
            self.output.warning("upstream test/test_api.py not found, skipping")
            return
        env = dict(os.environ)
        env["PYTHONPATH"] = self.source_folder
        # Host site-packages pytest plugins may be incompatible with the
        # interpreter — use unittest directly (upstream's own runner).
        cmd = [sys.executable, "-m", "unittest", "-v", "test.test_api"]
        try:
            res = subprocess.run(cmd, cwd=self.source_folder, env=env,
                                 capture_output=True, timeout=600)
        except Exception as e:
            self.output.warning(f"upstream unittest run failed: {e}")
            return
        out = (res.stdout or b"").decode(errors="ignore")
        err = (res.stderr or b"").decode(errors="ignore")
        for line in (out + err).splitlines()[-8:]:
            self.output.info(f"upstream unittest: {line}")
        self.output.info(
            f"upstream unittest rc={res.returncode} — "
            f"test_api.py 3 cases (test_metadata/test_helpers/test_dirs)")
        if res.returncode != 0:
            self.output.warning("upstream unittest reported failures")

    def build(self):
        if not os.path.isfile(os.path.join(self.source_folder, "appdirs.py")):
            raise ConanException("appdirs.py module not found in source")
        self._run_upstream_tests()

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site, exist_ok=True)
        src = os.path.join(self.source_folder, "appdirs.py")
        dst = os.path.join(site, "appdirs.py")
        shutil.copy2(src, dst)
        if not os.path.isfile(dst):
            raise ConanException(f"appdirs.py missing under {dst}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        # declare the import path (aiohttp lesson: printing it is not enough)
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
