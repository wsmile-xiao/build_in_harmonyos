#!/usr/bin/env python3
"""Conan recipe for anytree 2.13.0 — tree data structure library.

HarmonyOS PC adaptation: pure-Python package copied into site-packages.

Unlike the flat Python packages adapted earlier (markupsafe / itsdangerous /
pycparser), anytree ships **sub-packages** (``exporter/`` ``importer/``
``iterators/`` ``node/`` ``util/``), so the whole ``src/anytree`` tree must be
copied recursively rather than file-by-file.

Dependencies: none at runtime (``pyproject.toml`` declares ``dependencies = []``).

Upstream builds with **pdm-backend** (``[tool.pdm.build] includes = ["src/anytree"]``
and ``[tool.pdm.version] source = "scm"``), but like the other Python packages in
this archive this recipe does **not** run a PEP 517 build — the importable
``anytree/`` tree is copied verbatim. No ``build_requires`` are needed, which
also avoids depending on ``pdm-backend`` (not published on ohpcd).

Two upstream quirks worth recording:

* **Stale ``__version__``**: ``src/anytree/__init__.py`` says
  ``__version__ = "2.12.1"`` while the distribution is **2.13.0** (PKG-INFO and
  the tarball name both say 2.13.0). The consumer test therefore pins the *real*
  module value (2.12.1) so the mismatch is documented rather than assumed away —
  see notes.md.
* **Upstream tests need an unpublished dev dependency**: 4 of the 26 test files
  import ``test2ref`` (a ``[dependency-groups]`` dev tool, not a runtime dep and
  not on ohpcd). Since the import happens at collection time, those 4 files abort
  the whole run; with them ignored the remaining suite is 143 passed.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Tests importing test2ref (unpublished dev tool) — collection fails on these,
# so they are excluded explicitly and the reason is reported (R51).
_TESTS_NEEDING_TEST2REF = (
    "tests/test_dotexport.py",
    "tests/test_dotexporter.py",
    "tests/test_mermaidexporter.py",
    "tests/test_uniquedotexporter.py",
)


class AnytreeConan(ConanFile):
    name = "anytree"
    version = "2.13.0"
    description = "Powerful and Lightweight Python Tree Data Structure"
    license = "Apache-2.0"
    homepage = "https://github.com/c0fec0de/anytree"
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
        env["PYTHONPATH"] = os.path.join(self.source_folder, "src")
        # Site-packages pytest plugins may be incompatible with the host
        # interpreter (host pytest 5.4.3 + typeguard on py3.12 dies while
        # importing conftest.py) — ignore them entirely, in the probe as well,
        # otherwise the probe itself reports pytest as unavailable.
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

        # Exclude the collection-blocking files, reporting why.
        ignored = [p for p in _TESTS_NEEDING_TEST2REF
                   if os.path.isfile(os.path.join(self.source_folder, p))]
        if ignored:
            self.output.warning(
                f"upstream tests: excluding {len(ignored)} file(s) that import "
                "'test2ref' at collection time — test2ref is a dev-group tool "
                "(not a runtime dependency) and is not published on ohpcd: "
                + ", ".join(os.path.basename(p) for p in ignored))
        try:
            cmd = [sys.executable, "-m", "pytest", "tests", "-q",
                   "--assert=plain", "-p", "no:cacheprovider"]
            for p in ignored:
                cmd.append(f"--ignore={p}")
            res = subprocess.run(cmd, cwd=self.source_folder, env=env,
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
        if not os.path.isdir(os.path.join(self.source_folder, "src", "anytree")):
            raise ConanException("src/anytree package directory not found")
        self._run_upstream_tests()

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        pkg_dst = os.path.join(site, "anytree")
        src = os.path.join(self.source_folder, "src", "anytree")
        # Recursive copy: anytree has sub-packages (exporter/ importer/
        # iterators/ node/ util/), unlike the flat packages adapted earlier.
        shutil.copytree(src, pkg_dst, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(
                            "__pycache__", "*.pyc", "*.pyo"))
        if not os.path.isfile(os.path.join(pkg_dst, "__init__.py")):
            raise ConanException(f"anytree package missing under {pkg_dst}")
        for sub in ("node", "iterators", "exporter", "importer", "util"):
            if not os.path.isfile(os.path.join(pkg_dst, sub, "__init__.py")):
                raise ConanException(f"anytree sub-package '{sub}' incomplete")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        # export the import path so consumers/test_package get it automatically
        # (lesson: aiohttp CI failed with "No module named 'multidict'" when
        # package_info only printed PYTHONPATH instead of declaring it)
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
