#!/usr/bin/env python3
"""Conan recipe for pycparser 3.0 — C99 parser in pure Python.

HarmonyOS PC adaptation: pure-Python package copied into site-packages.

Two upstream facts worth recording:

* **3.0 dropped the PLY dependency.** Earlier releases bundled/required ``ply``
  for the lexer and parser; 3.0 ships a hand-written lexer/parser
  (``pycparser/c_lexer.py``, ``pycparser/c_parser.py``) importing only the
  standard library (``dataclasses`` / ``enum`` / ``re`` / ``typing``). Verified
  by reading the sdist: zero occurrences of ``ply``/``lex.lex``/``yacc.yacc``,
  and no ``lextab``/``yacctab`` tables. So there is **no runtime dependency**
  on PLY — and, importantly, no need to adapt ``ply`` first (a big win for
  consumers such as cffi, which require pycparser).

* Upstream builds with setuptools (``setuptools>=69`` + ``wheel``), but like the
  other Python packages in this archive (markupsafe, itsdangerous, requests)
  this recipe does **not** run a PEP 517 build: the importable ``pycparser/``
  directory is copied verbatim. No ``build_requires`` are needed, which avoids
  depending on ``setuptools``/``wheel`` (neither is published on ohpcd).

``c_ast.py`` is shipped pre-generated in the sdist (generated upstream from
``_c_ast.cfg`` via ``_ast_gen.py``), so the packaging keeps both files but never
has to invoke the generator. ``_c_ast.cfg`` and ``_ast_gen.py`` are kept
because ``_ast_gen.py`` is also an importable utility module upstream.

Note: the sdist also contains a ``pycparser.egg-info/`` directory. Build
metadata like that is deliberately **not** copied — only ``pycparser/`` is.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PycparserConan(ConanFile):
    name = "pycparser"
    version = "3.0"
    description = "C99 parser in pure Python"
    license = "BSD-3-Clause"
    homepage = "https://github.com/eliben/pycparser"
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
        if not os.path.isdir(tests_dir):
            self.output.warning("upstream tests/ not found, skipping pytest")
            return
        env = dict(os.environ)
        # tests import ``pycparser`` from the source tree root (the package sits
        # directly at the top level, not under src/), so the cwd is enough.
        env["PYTHONPATH"] = self.source_folder
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
        if not os.path.isdir(os.path.join(self.source_folder, "pycparser")):
            raise ConanException("pycparser/ package directory not found")
        # Guard the no-PLY claim at build time: if a future packaging mixes in a
        # release that reintroduced PLY, fail loudly instead of shipping a
        # package whose import would raise ImportError for consumers.
        parser_src = os.path.join(self.source_folder, "pycparser", "c_parser.py")
        if os.path.isfile(parser_src):
            with open(parser_src, "r", encoding="utf-8", errors="replace") as f:
                head = f.read()
            if "import ply" in head or "from ply" in head:
                raise ConanException(
                    "pycparser now imports ply — a ply requirement must be "
                    "added (and ply adapted/published) before shipping")
        self._run_upstream_tests()

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        pkg_dir = os.path.join(site, "pycparser")
        os.makedirs(pkg_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "pycparser")
        for entry in sorted(os.listdir(src)):
            fpath = os.path.join(src, entry)
            if entry.endswith((".c", ".h")) or os.path.isdir(fpath):
                continue
            shutil.copy2(fpath, os.path.join(pkg_dir, entry))
        if not os.path.isfile(os.path.join(pkg_dir, "__init__.py")):
            raise ConanException(f"pycparser package missing under {pkg_dir}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        # export the import path so consumers/test_package get it automatically
        # (lesson: aiohttp CI failed with "No module named 'multidict'" when
        # package_info only printed PYTHONPATH instead of declaring it)
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
