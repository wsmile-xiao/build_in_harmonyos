#!/usr/bin/env python3
"""Conan recipe for Jinja2 2.10.1 — templating engine (pure Python, setuptools).

HarmonyOS PC adaptation:
  * one source patch is required — 0001-collections-abc.patch. Jinja2 2.10.1
    predates the py3.10 removal of the legacy aliases and imports
    ``collections.Mapping`` / ``MutableMapping`` / ``MutableSet`` /
    ``MutableSequence`` from five sites; the module cannot even be imported on
    the platform's Python 3.12 without the ``collections.abc`` rewrite.
  * runtime dependency markupsafe is pinned to 1.1.1 on purpose: jinja2/utils.py
    imports ``soft_unicode``, which MarkupSafe removed in 2.1.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Jinja2Conan(ConanFile):
    name = "jinja2"
    version = "2.10.1"
    description = "A very fast and expressive template engine"
    license = "BSD-3-Clause"
    homepage = "https://github.com/pallets/jinja"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def export_sources(self):
        # the source patch below must travel with the recipe
        export_conandata_patches(self)

    def requirements(self):
        # PyPI requires_dist: MarkupSafe>=0.23. Pinned to 1.1.1 because
        # jinja2/utils.py imports soft_unicode (gone in MarkupSafe 2.1).
        self.requires("markupsafe/1.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _site_packages(self, dep_name):
        """Resolve a python-require dependency's site-packages directory."""
        dep = self.dependencies.get(dep_name)
        if dep is None:
            return None
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(dep.package_folder, "lib", py_ver, "site-packages")
        return site if os.path.isdir(site) else None

    def _run_upstream_tests(self):
        """Run the upstream pytest suite and report the real pass rate (R51)."""
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_dir):
            self.output.warning("upstream tests/ not found, skipping pytest")
            return
        env = dict(os.environ)
        paths = [self.source_folder]
        dep_site = self._site_packages("markupsafe")
        if dep_site:
            paths.append(dep_site)
        env["PYTHONPATH"] = os.pathsep.join(paths)
        # Host site-packages plugins can be incompatible with the interpreter
        # (host pytest 5.4.3 + typeguard on py3.12 dies importing conftest) —
        # disable them for the probe as well, else pytest looks unavailable.
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        try:
            probe = subprocess.run(
                [sys.executable, "-m", "pytest", "--version"],
                env=env, capture_output=True, timeout=60)
            if probe.returncode != 0:
                self.output.warning("pytest unavailable, upstream tests skipped")
                return
        except Exception as e:
            self.output.warning(f"pytest unavailable, upstream tests skipped: {e}")
            return
        try:
            res = subprocess.run(
                # --assert=plain: this pytest's assertion-rewrite hook is
                # incompatible with py3.12 bytecode; plain asserts still fail
                # the run on any assertion error.
                [sys.executable, "-m", "pytest", "tests", "-q", "--assert=plain",
                 "-p", "no:cacheprovider"],
                cwd=self.source_folder, env=env,
                capture_output=True, timeout=900)
            out = res.stdout.decode(errors="ignore").strip()
            self.output.info(
                f"upstream pytest: {out.splitlines()[-1] if out else 'n/a'}")
            if res.returncode != 0:
                self.output.warning("upstream pytest reported failures")
        except Exception as e:
            self.output.warning(f"upstream pytest run failed: {e}")

    def build(self):
        if not os.path.isdir(os.path.join(self.source_folder, "jinja2")):
            raise ConanException("jinja2 package directory not found")
        self._run_upstream_tests()

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        pkg_dir = os.path.join(site, "jinja2")
        os.makedirs(pkg_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "jinja2")
        for entry in sorted(os.listdir(src)):
            fpath = os.path.join(src, entry)
            if os.path.isdir(fpath):
                # ship the jinja2 subpackages (e.g. nothing today, but be safe)
                if entry == "__pycache__":
                    continue
                shutil.copytree(fpath, os.path.join(pkg_dir, entry),
                                ignore=shutil.ignore_patterns("__pycache__"))
                continue
            if entry.endswith((".c", ".h", ".so")):
                continue
            shutil.copy2(fpath, os.path.join(pkg_dir, entry))
        if not os.path.isfile(os.path.join(pkg_dir, "__init__.py")):
            raise ConanException(f"jinja2 package missing under {pkg_dir}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        # declare the import path (aiohttp lesson: printing it is not enough —
        # CI failed with "No module named 'multidict'")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
