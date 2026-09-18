#!/usr/bin/env python3
"""Conan recipe for docopt 0.6.2 — command-line argument parser
(pure Python single-module library, setuptools, zero runtime dependencies).

HarmonyOS PC adaptation: ``docopt`` is a single top-level module
(``py_modules=['docopt']``), not a package, so ``docopt.py`` is copied straight
into site-packages. No source patch is needed on Python 3.12 — the module only
emits ``SyntaxWarning`` for a few non-raw regex string literals
(e.g. ``re.findall('(<\\S*?>)', source)``), which is cosmetic and does not
affect parsing behaviour (upstream suite: 39 passed).

R38 note: setup.py declares neither ``entry_points`` nor ``scripts`` and the
sdist ships no bin/ payload — a library only, hence no commands.json.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class DocoptConan(ConanFile):
    name = "docopt"
    version = "0.6.2"
    description = "Pythonic argument parser, that will make you smile"
    license = "MIT"
    homepage = "https://github.com/docopt/docopt"
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
        self._fetch_upstream_tests()

    def _fetch_upstream_tests(self):
        """docopt's PyPI sdist ships no tests — fetch them from the official
        GitHub tag (same build-time-download pattern as antlr4-python3-runtime /
        adcli in this archive). test_docopt.py goes to tests/ while the
        .docopt case file + its conftest.py go to tests/cases/ — keeping the
        conftest out of tests/ means running test_docopt.py alone never
        imports the legacy ``pytest_collect_file`` hook, which newer pytest
        versions reject at import time.
        """
        import hashlib
        import urllib.request

        for spec in self.conan_data.get("test_sources", []):
            dest = os.path.join(self.source_folder, spec["dest"])
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                req = urllib.request.Request(
                    spec["url"], headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(req, timeout=120).read()
                want = spec.get("sha256")
                got = hashlib.sha256(data).hexdigest()
                if want and got != want:
                    self.output.warning(
                        f"upstream test {spec['dest']} sha256 mismatch: "
                        f"got {got}, want {want} — discarded")
                    continue
                with open(dest, "wb") as fh:
                    fh.write(data)
                self.output.info(f"fetched upstream test {spec['dest']} "
                                 f"({len(data)} bytes)")
            except Exception as e:
                self.output.warning(
                    f"upstream test download failed for {spec['dest']}: {e}")

    def _run_upstream_tests(self):
        """Run the upstream pytest suite and report the real pass rate (R51).

        The upstream suite (test_docopt.py + testcases.docopt) is NOT shipped in
        the PyPI sdist — it lives in the upstream git repository only, and
        conandata.yml downloads those two files into tests/ at source() time.
        """
        tests_dir = os.path.join(self.source_folder, "tests")
        test_file = os.path.join(tests_dir, "test_docopt.py")
        if not os.path.isfile(test_file):
            self.output.warning(
                "upstream tests not present (test_docopt.py missing) — skipped")
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
            if probe.returncode != 0:
                self.output.warning("pytest unavailable, upstream tests skipped")
                return
        except Exception as e:
            self.output.warning(f"pytest unavailable, upstream tests skipped: {e}")
            return

        def _run(target):
            try:
                res = subprocess.run(
                    # --assert=plain: this pytest's assertion-rewrite hook is
                    # incompatible with py3.12 bytecode.
                    [sys.executable, "-m", "pytest", target, "-q",
                     "--assert=plain", "-p", "no:cacheprovider"],
                    cwd=self.source_folder, env=env,
                    capture_output=True, timeout=600)
                out = res.stdout.decode(errors="ignore").strip()
                last = out.splitlines()[-1] if out else "n/a"
                self.output.info(f"upstream pytest [{target}]: {last}")
                if res.returncode != 0:
                    self.output.warning(
                        f"upstream pytest reported failures [{target}]")
            except Exception as e:
                self.output.warning(f"upstream pytest run failed [{target}]: {e}")

        _run("tests/test_docopt.py")
        # case-file suite (custom conftest collector) — best effort: newer
        # pytest drops the legacy pytest_collect_file API it relies on
        if os.path.isfile(os.path.join(tests_dir, "cases", "testcases.docopt")):
            _run("tests/cases/testcases.docopt")

    def build(self):
        if not os.path.isfile(os.path.join(self.source_folder, "docopt.py")):
            raise ConanException("docopt.py module not found in source")
        self._run_upstream_tests()

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site, exist_ok=True)
        src = os.path.join(self.source_folder, "docopt.py")
        dst = os.path.join(site, "docopt.py")
        shutil.copy2(src, dst)
        if not os.path.isfile(dst):
            raise ConanException(f"docopt.py missing under {site}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        # declare the import path (aiohttp lesson: printing it is not enough —
        # CI failed with "No module named 'multidict'")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
