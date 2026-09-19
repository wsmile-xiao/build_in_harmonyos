#!/usr/bin/env python3
"""Conan recipe for itsdangerous 2.2.0 — data signing/serialisation library.

HarmonyOS PC adaptation: pure-Python package copied into site-packages.

Upstream uses flit_core as its build backend, but this recipe does not invoke a
PEP 517 build at all: like the other Python packages in this archive
(markupsafe, requests, docopt, ...), the importable ``itsdangerous/`` directory
is copied verbatim. No build_requires are therefore needed — which also avoids
depending on ``flit_core``/``setuptools``, neither of which is published on
ohpcd.

Dependencies: none at runtime (verified against the sdist's pyproject.toml,
which declares no ``dependencies``).

Note on ``__version__``: itsdangerous resolves it lazily via
``importlib.metadata.version("itsdangerous")`` (``__init__.py`` __getattr__).
That lookup walks sys.path for a ``.dist-info`` directory, which this
packaging intentionally does not ship, so ``__version__`` is NOT part of the
contract asserted by the consumer test — the public API surface is.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ItsdangerousConan(ConanFile):
    name = "itsdangerous"
    version = "2.2.0"
    description = "Safely pass data to untrusted environments and back"
    license = "BSD-3-Clause"
    homepage = "https://github.com/pallets/itsdangerous"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _run_upstream_tests(self):
        """Run the upstream pytest suite and report the real pass rate (R51)."""
        tests_dir = os.path.join(self.source_folder, "tests")
        src_dir = os.path.join(self.source_folder, "src")
        if not os.path.isdir(tests_dir):
            self.output.warning("upstream tests/ not found, skipping pytest")
            return
        env = dict(os.environ)
        env["PYTHONPATH"] = src_dir
        # Site-packages pytest plugins may be incompatible with the host
        # interpreter (host pytest 5.4.3 + typeguard on py3.12 dies with
        # "TypeError: required field lineno missing from alias" while importing
        # conftest.py) — ignore them entirely, in the probe as well, otherwise
        # the probe itself reports pytest as unavailable.
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
                # --assert=plain: the rewrite hook of the available pytest is
                # incompatible with py3.12 bytecode; plain assert still fails
                # the run on any assertion error.
                [sys.executable, "-m", "pytest", "tests", "-q", "--assert=plain",
                 "-p", "no:cacheprovider"],
                cwd=self.source_folder, env=env,
                capture_output=True, timeout=600)
            out = res.stdout.decode(errors="ignore").strip()
            self.output.info(
                f"upstream pytest: {out.splitlines()[-1] if out else 'n/a'}")
            if res.returncode != 0:
                self.output.warning("upstream pytest reported failures")
        except Exception as e:
            self.output.warning(f"upstream pytest run failed: {e}")

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isdir(os.path.join(self.source_folder, "src", "itsdangerous")):
            raise ConanException("src/itsdangerous package directory not found")
        self._run_upstream_tests()

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        pkg_dir = os.path.join(site, "itsdangerous")
        os.makedirs(pkg_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "src", "itsdangerous")
        for entry in sorted(os.listdir(src)):
            if entry.endswith((".c", ".h")):
                continue  # no C sources upstream; kept for symmetry with siblings
            fpath = os.path.join(src, entry)
            if os.path.isdir(fpath):
                continue
            shutil.copy2(fpath, os.path.join(pkg_dir, entry))
        if not os.path.isfile(os.path.join(pkg_dir, "__init__.py")):
            raise ConanException(f"itsdangerous package missing under {pkg_dir}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        # export the import path so consumers/test_package get it automatically
        # (lesson: aiohttp CI failed with "No module named 'multidict'" when
        # package_info only printed PYTHONPATH instead of declaring it)
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
