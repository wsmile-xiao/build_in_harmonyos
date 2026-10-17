#!/usr/bin/env python3
"""Conan recipe for markupsafe 3.0.3 — HTML/XML safe string library.

HarmonyOS PC adaptation: packages the **pure-Python fallback** of markupsafe.

The optional C accelerator (``src/markupsafe/_speedups.c``) is deliberately not
built. ``markupsafe/__init__.py`` degrades gracefully::

    try:
        from ._speedups import _escape_inner
    except ImportError:
        from ._native import _escape_inner

so the pure-Python path is a fully supported upstream mode. Building the .so
instead would bind the **build host's** CPython ABI and architecture into a
``python-require`` package, which the consumer machine need not match — the same
pure-Python mode used by markupsafe 1.1.1 / yarl / frozenlist / aiohttp in this
archive.

Dependencies: none at runtime. ``typing_extensions`` appears in
``markupsafe/__init__.py`` but only inside ``if t.TYPE_CHECKING:`` (verified),
so it is a type-checker-only import and must NOT become a requirement.

Version coexistence note: markupsafe 3.0.3 **removed** ``soft_unicode`` (it was
deprecated in 2.0 and removed in 2.1). Jinja2 2.10.1 imports ``soft_unicode``
(``jinja2/utils.py``), so that Jinja2 requires markupsafe <= 2.0.1 while newer
Jinja2 (3.1.x) requires >= 2.1.1. Both versions must be publishable side by
side in the same remote.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MarkupsafeConan(ConanFile):
    name = "markupsafe"
    version = "3.0.3"
    description = "Safely add untrusted strings to HTML/XML markup"
    license = "BSD-3-Clause"
    homepage = "https://github.com/pallets/markupsafe"
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
        if not os.path.isdir(os.path.join(self.source_folder, "src", "markupsafe")):
            raise ConanException("src/markupsafe package directory not found")
        self._run_upstream_tests()

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        pkg_dir = os.path.join(site, "markupsafe")
        os.makedirs(pkg_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "src", "markupsafe")
        for entry in sorted(os.listdir(src)):
            if entry.endswith((".c", ".h")):
                continue  # C accelerator source not shipped (pure-Python mode)
            fpath = os.path.join(src, entry)
            if os.path.isdir(fpath):
                continue
            shutil.copy2(fpath, os.path.join(pkg_dir, entry))
        if not os.path.isfile(os.path.join(pkg_dir, "__init__.py")):
            raise ConanException(f"markupsafe package missing under {pkg_dir}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        # export the import path so consumers/test_package get it automatically
        # (lesson: aiohttp CI failed with "No module named 'multidict'" when
        # package_info only printed PYTHONPATH instead of declaring it)
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
