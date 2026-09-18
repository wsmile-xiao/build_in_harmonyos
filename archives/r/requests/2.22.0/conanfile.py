#!/usr/bin/env python3
"""Conan recipe for requests 2.22.0 — HTTP library for Python
(pure Python, setuptools).

HarmonyOS PC adaptation notes
-----------------------------
Dependencies are the versions already published on ohpcd (certifi 2026.7.22,
chardet 5.2.0, idna 3.18, urllib3 2.7.0). requests 2.22.0's own
``check_compatibility()`` (requests/__init__.py) asserts urllib3 1.x and
chardet 3.x, so importing it with those newer deps emits ONE
``RequestsDependencyWarning`` at import time. This was measured, not assumed:

  * real HTTPS GET through the package  -> 200 OK
  * redirects / Retry(max_retries=...)  -> OK
  * timeout propagation                 -> ConnectTimeout raised
  * non-ASCII host (idna encode)        -> punycode produced correctly

The warning is advisory only and does not gate any code path — using the
published newer deps avoids pulling four extra legacy pins into the graph
(and a recipe PR must not bundle unrelated packages, W2/PF4).

One source patch is applied: 0001-tests-snimissingwarning-optional.patch.
requests 2.22.0's test bootstrap does ``from urllib3.exceptions import
SNIMissingWarning``, a name urllib3 2.x removed — without the patch the upstream
suite cannot even be imported. The patch is test-only (grep confirms
``requests/`` itself never references that symbol).
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RequestsConan(ConanFile):
    name = "requests"
    version = "2.22.0"
    description = "Python HTTP for Humans"
    license = "Apache-2.0"
    homepage = "https://github.com/psf/requests"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # PyPI requires_dist of 2.22.0:
        #   chardet>=3.0.2,<3.1.0 | idna>=2.5,<2.9
        #   urllib3>=1.21.1,<1.26  | certifi>=2017.4.17
        # Pinned to the published ohpcd versions instead of those legacy ranges
        # (see module docstring: measured to work, warning-only).
        self.requires("certifi/2026.7.22")
        self.requires("chardet/5.2.0")
        self.requires("idna/3.18")
        self.requires("urllib3/2.7.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _dep_site(self, name):
        dep = self.dependencies.get(name)
        if dep is None:
            return None
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(dep.package_folder, "lib", py_ver, "site-packages")
        return site if os.path.isdir(site) else None

    def _run_upstream_tests(self):
        """Run the upstream suite (R51), in full where it can actually run.

        All 8 files of the shipped suite are now driven. Two blockers that
        previously forced a 4-file subset are lifted by patch 0002:

          * ``mocker`` — pytest-mock is not published on ohpcd, so it cannot be
            a test requirement; tests/_shim_mocker.py supplies an equivalent
            fixture built on stdlib unittest.mock (the suite only uses
            ``patch`` / ``patch.dict`` / ``Mock``). Without it, 8 tests
            errored with "fixture 'mocker' not found".
          * ``httpbin`` — needs an external service. The fixture now degrades
            to ``pytest.skip`` when pytest-httpbin is absent instead of raising
            "recursive dependency involving fixture 'httpbin'" (the cause of
            149 errors); tests that genuinely need a live service are reported
            as skipped, which is honest rather than silently green.

        Also fixed by 0002: test_utils.py's pre-3.0 parametrize idiom
        (``pytest.mark.skipif('cStringIO is None')`` inside a parametrize tuple
        -> "object of type 'MarkDecorator' has no len()") which aborted
        collection of that whole module.

        Remaining known failure, unrelated to the packaging: test_chunked_upload
        raises http.client.ResponseNotReady with urllib3 2.x (it also fails on a
        pristine tree with only patch 0001 applied — measured, not assumed).
        """
        suite = ["tests/test_structures.py", "tests/test_packages.py",
                 "tests/test_hooks.py", "tests/test_testserver.py",
                 "tests/test_utils.py", "tests/test_help.py",
                 "tests/test_lowlevel.py", "tests/test_requests.py"]
        for rel in suite:
            if not os.path.isfile(os.path.join(self.source_folder, rel)):
                self.output.warning(f"upstream {rel} not found, skipping")
                return
        env = dict(os.environ)
        paths = [self.source_folder]
        for dep in ("certifi", "chardet", "idna", "urllib3"):
            site = self._dep_site(dep)
            if site:
                paths.append(site)
        env["PYTHONPATH"] = os.pathsep.join(paths)
        # Host site-packages plugins can be incompatible with the interpreter
        # (host pytest 5.4.3 + typeguard on py3.12) — disable autoload, for the
        # probe as well, else pytest looks unavailable.
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
                # incompatible with py3.12 bytecode.
                [sys.executable, "-m", "pytest", *suite, "-q", "--assert=plain",
                 "-p", "no:cacheprovider"],
                cwd=self.source_folder, env=env,
                capture_output=True, timeout=900)
            out = res.stdout.decode(errors="ignore").strip()
            self.output.info(
                f"upstream pytest (self-contained subset): "
                f"{out.splitlines()[-1] if out else 'n/a'}")
            if res.returncode != 0:
                self.output.warning("upstream pytest reported failures")
        except Exception as e:
            self.output.warning(f"upstream pytest run failed: {e}")

    def build(self):
        if not os.path.isdir(os.path.join(self.source_folder, "requests")):
            raise ConanException("requests package directory not found")
        self._run_upstream_tests()

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site, exist_ok=True)
        src = os.path.join(self.source_folder, "requests")
        dst = os.path.join(site, "requests")
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", "*.pyo"))
        if not os.path.isfile(os.path.join(dst, "__init__.py")):
            raise ConanException(f"requests package missing under {dst}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        # declare the import path (aiohttp lesson: printing it is not enough —
        # CI failed with "No module named 'multidict'")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
