#!/usr/bin/env python3
"""Conan recipe for libcharon 5.0.0 — pure Python library (Ultimaker libCharon).

Upstream: https://github.com/Ultimaker/libCharon (tag 5.0.0), LGPL-3.0.
File metadata and streaming library for 3D-printing packages (UFP/G-code).

HarmonyOS PC adaptation: 100% pure Python (stdlib only: zipfile, json,
xml, typing — no C extensions, no third-party runtime deps), so no OHOS
source change is needed or made. build() copies nothing compiled: it runs
the FULL upstream pytest suite for real on the worker (37 cases under
tests/, pytest.ini: testpaths=tests, python_files=Test*.py) and reports
the real pass rate, then package() copies the Charon/ package dir into
site-packages layout.

pytest is NOT a Conan dep: it is installed into a PRIVATE directory
(build_folder/pydeps) via `pip install --target` from the internal mirror,
pinned to the version validated on this platform. This is deliberate: the
CI worker may have no usable pytest, and PYTHONNOUSERSITE=1 is forced so a
foreign user-site cannot shadow the run (lesson from gym 0.26.2).
pytest itself is pure Python, so no .so signing/ownership workarounds apply.
"""
import json
import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout

# Audited upstream test total (pytest expanded cases): 12 (TestGCodeFile) +
# 2 (TestGCodeFormat) + 23 (TestOpenPackagingConvention, 12 defs expanded via
# @pytest.mark.parametrize) = 37. Verified against tag 5.0.0 sources and the
# true-machine collect-only result (37 items).
UPSTREAM_TEST_TOTAL = 37
PYTEST_PIN = "8.3.4"
INDEX_URL = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"


class LibcharonConan(ConanFile):
    name = "libcharon"
    version = "5.0.0"
    description = "File metadata and streaming library (Ultimaker Charon, UFP/G-code packages)"
    license = "LGPL-3.0-only"
    homepage = "https://github.com/Ultimaker/libCharon"
    url = "https://github.com/Ultimaker/libCharon"

    package_type = "python-require"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isdir(os.path.join(self.source_folder, "Charon")):
            raise ConanException("Charon/ package dir not found in source")
        self._run_upstream_tests()

    # ------------------------------------------------ private helpers
    def _py(self):
        return sys.executable or "python3"

    def _pyenv(self, pydeps):
        env = dict(os.environ)
        env["PYTHONNOUSERSITE"] = "1"
        env["PYTHONPATH"] = os.pathsep.join([pydeps, self.source_folder])
        return env

    def _ensure_pytest(self, py, env, pydeps):
        """Return True once `py -m pytest` works under env."""
        try:
            res = subprocess.run([py, "-m", "pytest", "--version"],
                                 cwd=self.build_folder, env=env,
                                 capture_output=True, timeout=60)
            if res.returncode == 0:
                self.output.info("pytest: %s" % (res.stdout or b"").decode(
                    errors="ignore").splitlines()[0])
                return True
        except Exception as exc:
            self.output.warning("pytest probe error: %s" % exc)
        for pinned in (True, False):
            spec = "pytest==%s" % PYTEST_PIN if pinned else "pytest"
            self.output.info("pip install --target pydeps %s (%s)" % (
                spec, "pinned" if pinned else "unpinned fallback"))
            try:
                res = subprocess.run(
                    [py, "-m", "pip", "install", "--quiet",
                     "--index-url", INDEX_URL,
                     "--trusted-host", "pypi.cnb.cool",
                     "--target", pydeps, "--ignore-installed", spec],
                    env=env, capture_output=True, timeout=600)
                if res.returncode != 0:
                    self.output.warning("pip install %s failed rc=%s: %s" % (
                        spec, res.returncode,
                        (res.stderr or b"").decode(errors="ignore")[-300:]))
                    continue
            except Exception as exc:
                self.output.warning("pip install error: %s" % exc)
                continue
            try:
                res = subprocess.run([py, "-m", "pytest", "--version"],
                                     cwd=self.build_folder, env=env,
                                     capture_output=True, timeout=60)
                if res.returncode == 0:
                    return True
            except Exception as exc:
                self.output.warning("pytest probe error after install: %s" % exc)
        return False

    def _parse_pytest_summary(self, log):
        """Parse the single pytest summary line (deterministic source).

        pytest -q prints exactly one result line such as
        `37 passed in 0.51s` or `2 failed, 35 passed in 0.61s`.
        All counters come from that one line; no string counting elsewhere.
        """
        summary = [line for line in log.splitlines()
                   if re.search(r"\d+ (passed|failed|skipped|error)", line)]
        if not summary:
            raise ConanException(
                "no pytest summary line found; refusing to continue. "
                "log tail:\n%s" % log[-2000:])
        last = summary[-1]
        # findall returns (number, word) tuples; index by word for lookup.
        counters = {word: int(num) for num, word in
                    re.findall(r"(\d+)\s(passed|failed|skipped|error)", last)}
        passed = int(counters.get("passed", 0))
        failed = int(counters.get("failed", 0))
        skipped = int(counters.get("skipped", 0))
        errors = int(counters.get("error", 0))
        failed += errors
        executed = passed + failed
        discovered = executed + skipped
        # Self-check identities (passed + failed == executed,
        # executed + skipped <= discovered); fix the source, never the numbers.
        assert passed + failed == executed
        assert executed + skipped <= discovered
        for value in (passed, failed, skipped, executed, discovered):
            assert isinstance(value, int) and value >= 0
        return discovered, executed, passed, failed, skipped, last

    def _run_upstream_tests(self):
        """Run the full upstream pytest suite (L1c) — real, unmodified."""
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_dir):
            raise ConanException("upstream tests/ not found in source")
        # Falsifiability: fixtures must be real (non-empty); an empty
        # fixture set would pass vacuously (toybox tar-B lesson).
        for fixture in ("tests/filetypes/resources/um3.gcode",
                        "tests/filetypes/resources/um3.gcode.gz",
                        "tests/filetypes/resources/hello.opc",
                        "tests/filetypes/resources/empty.opc"):
            path = os.path.join(self.source_folder, fixture)
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                raise ConanException("upstream fixture missing or empty: %s" % fixture)
            self.output.info("fixture %s size=%d" % (fixture, os.path.getsize(path)))
        py = self._py()
        pydeps = os.path.join(self.build_folder, "pydeps")
        os.makedirs(pydeps, exist_ok=True)
        env = self._pyenv(pydeps)
        if not self._ensure_pytest(py, env, pydeps):
            raise ConanException(
                "pytest unavailable (pip install failed); missing test "
                "runner must be fixed before measuring — refusing to continue.")
        # Deterministic denominator cross-check: --collect-only must agree
        # with the audited total before the suite runs.
        try:
            res = subprocess.run(
                [py, "-m", "pytest", "tests/", "--collect-only", "-q",
                 "-p", "no:cacheprovider"],
                cwd=self.source_folder, env=env,
                capture_output=True, timeout=300)
        except Exception as exc:
            raise ConanException("pytest collect-only run error: %s" % exc)
        collect_out = ((res.stdout or b"") + b"\n" + (res.stderr or b"")).decode(
            errors="ignore")
        collected = len(re.findall(r"^tests?/.*::", collect_out, re.MULTILINE))
        if collected == 0:
            # Fallback single source: the "N tests collected" trailer line.
            match = re.search(r"(\d+) tests? collected", collect_out)
            collected = int(match.group(1)) if match else 0
        self.output.info("pytest collect-only: %d items" % collected)
        if collected != UPSTREAM_TEST_TOTAL:
            raise ConanException(
                "upstream test total changed (collected %d, audited %d); "
                "refusing to continue with an unverified denominator." % (
                    collected, UPSTREAM_TEST_TOTAL))
        cmd = [py, "-m", "pytest", "tests/", "-q", "--no-header",
               "-p", "no:cacheprovider", "--tb=short"]
        command = "python -m pytest tests/ -q --no-header -p no:cacheprovider --tb=short"
        try:
            res = subprocess.run(cmd, cwd=self.source_folder, env=env,
                                 capture_output=True, timeout=900)
        except Exception as exc:
            raise ConanException("upstream pytest run error: %s" % exc)
        log = ((res.stdout or b"") + b"\n" + (res.stderr or b"")).decode(
            errors="ignore")
        for line in log.splitlines()[-8:]:
            self.output.info("pytest | %s" % line)
        discovered, executed, passed, failed, skipped, summary = \
            self._parse_pytest_summary(log)
        self.output.info("upstream pytest: %s" % summary)
        self.output.info("upstream counts: discovered=%d executed=%d passed=%d "
                         "failed=%d skipped=%d" % (
                             discovered, executed, passed, failed, skipped))
        if discovered != UPSTREAM_TEST_TOTAL:
            raise ConanException(
                "upstream result total changed (got %d, audited %d); refusing "
                "to continue with an unverified denominator." % (
                    discovered, UPSTREAM_TEST_TOTAL))
        status = "passed" if (failed == 0 and res.returncode == 0) else "failed"
        if status == "failed":
            self.output.warning(
                "upstream pytest has failures (rc=%s) — real numbers reported "
                "above and in the marker; see test_package/MANIFEST.yml." % res.returncode)
        upstream = {
            "status": status,
            "framework": "pytest",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(marker, flush=True)
        self.output.info(marker)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8", newline="\n") as handle:
                json.dump(upstream, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            self.output.warning("write hmbs_upstream.json failed: %s" % exc)

    # ------------------------------------------------ package
    def package(self):
        pkg_dir = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        os.makedirs(pkg_dir, exist_ok=True)
        shutil.copytree(os.path.join(self.source_folder, "Charon"),
                        os.path.join(pkg_dir, "Charon"),
                        dirs_exist_ok=True)
        copy(self, "LICENSE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
