#!/usr/bin/env python3
"""Conan recipe for pathspec 0.6.0 — gitignore-style path pattern matching
(pure Python, setuptools, zero runtime dependencies).

HarmonyOS PC adaptation: the package is a pure-Python library installed into
site-packages. No source patch is needed — pathspec/compat.py already prefers
``collections.abc.Collection`` and only falls back to the legacy
``collections.Container`` alias on Python < 3.6, so nothing here breaks on the
platform's Python 3.12.

R38 note: upstream declares no console_scripts entry point and ships no bin/
payload (setup.py has neither ``scripts=`` nor ``entry_points=``) — the package
is a library only, hence no commands.json.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class PathspecConan(ConanFile):
    name = "pathspec"
    version = "0.6.0"
    description = "Utility library for gitignore style pattern matching of file paths"
    license = "MPL-2.0"
    homepage = "https://github.com/cpburnz/python-path-specification"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def requirements(self):
        # PyPI requires_dist: none (zero runtime dependencies)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _run_upstream_tests(self):
        """Run the upstream test suite and report the real pass rate (R51).

        The suite lives inside the package (pathspec/tests/) and is unittest
        based. ``python -m pytest`` is used when available because it reports
        the counts in one line; otherwise fall back to unittest discovery.
        """
        tests_dir = os.path.join(self.source_folder, "pathspec", "tests")
        if not os.path.isdir(tests_dir):
            self.output.warning("upstream pathspec/tests not found, skipping")
            return
        env = dict(os.environ)
        env["PYTHONPATH"] = self.source_folder
        # Host site-packages plugins may be incompatible with the interpreter
        # (host pytest 5.4.3 + typeguard dies on py3.12 while importing) —
        # disable them for the probe too, else pytest looks unavailable.
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        try:
            probe = subprocess.run(
                [sys.executable, "-m", "pytest", "--version"],
                env=env, capture_output=True, timeout=60)
            has_pytest = probe.returncode == 0
        except Exception:
            has_pytest = False
        if has_pytest:
            try:
                res = subprocess.run(
                    # --assert=plain: this pytest's assertion-rewrite hook is
                    # incompatible with py3.12 bytecode.
                    [sys.executable, "-m", "pytest", "pathspec/tests", "-q",
                     "--assert=plain", "-p", "no:cacheprovider"],
                    cwd=self.source_folder, env=env,
                    capture_output=True, timeout=600)
                out = res.stdout.decode(errors="ignore").strip()
                self.output.info(
                    f"upstream pytest: {out.splitlines()[-1] if out else 'n/a'}")
                if res.returncode != 0:
                    self.output.warning("upstream pytest reported failures")
                return
            except Exception as e:
                self.output.warning(f"upstream pytest run failed: {e}")
        # unittest fallback
        try:
            res = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-v",
                 "-s", "pathspec/tests", "-t", "."],
                cwd=self.source_folder, env=env,
                capture_output=True, timeout=600)
            tail = res.stderr.decode(errors="ignore").strip().splitlines()[-3:]
            self.output.info(f"upstream unittest: {' | '.join(tail)}")
            if res.returncode != 0:
                self.output.warning("upstream unittest reported failures")
        except Exception as e:
            self.output.warning(f"upstream unittest run failed: {e}")

    def build(self):
        if not os.path.isdir(os.path.join(self.source_folder, "pathspec")):
            raise ConanException("pathspec package directory not found")
        self._run_upstream_tests()

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site, exist_ok=True)
        src = os.path.join(self.source_folder, "pathspec")
        dst = os.path.join(site, "pathspec")
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", "*.pyo"))
        if not os.path.isfile(os.path.join(dst, "__init__.py")):
            raise ConanException(f"pathspec package missing under {dst}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        # declare the import path (aiohttp lesson: printing it is not enough —
        # CI failed with "No module named 'multidict'")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
