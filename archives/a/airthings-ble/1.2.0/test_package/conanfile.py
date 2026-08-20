#!/usr/bin/env python3
"""Conan test_package for airthings-ble 1.2.0 — consumer check.

Runs two things against the package installed by THIS conan recipe:
  1. test_airthings_ble.py (real test source, L0c) — consumer API check.
  2. The upstream pytest suite (copied into test_package/tests/, pure
     hex-data decoding logic, no BLE hardware) — emits the
     HMBS_UPSTREAM_TEST_RESULT marker with real pytest counts.

PYTHONPATH injection: airthings-ble is a pure Python library whose runtime
deps (bleak, bleak-retry-connector, async-interrupt, cbor2) were pip-installed
into the same site-packages by the recipe's build(), so this package's own
site-packages is sufficient.
"""
import json
import os
import re
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException


class AirthingsBleTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_site_packages(self, pkg):
        """site-packages lives under lib/python3.x/site-packages — walk to locate it."""
        for root, _dirs, _files in os.walk(pkg):
            if os.path.basename(root) == "site-packages":
                return root
        return None

    def _run_upstream_tests(self, sp):
        """Run the copied upstream pytest suite and emit HMBS_UPSTREAM_TEST_RESULT."""
        tests_dir = os.path.join(os.path.dirname(__file__), "tests")
        if not os.path.isdir(tests_dir):
            raise ConanException(f"upstream tests/ not copied into test_package: {tests_dir}")
        env = dict(os.environ)
        env["PYTHONPATH"] = sp
        python = sys.executable
        # Ensure pytest is available (install from the mirror if missing).
        try:
            probe = subprocess.run(
                [python, "-m", "pytest", "--version"],
                env=env, capture_output=True, timeout=60,
            )
            if probe.returncode != 0:
                raise OSError("pytest unavailable")
        except Exception:
            self.output.info("installing pytest from mirror")
            subprocess.run(
                [python, "-m", "pip", "install", "pytest"],
                env=env, capture_output=True, timeout=300,
            )
        cmd = [
            python, "-m", "pytest", tests_dir, "-q", "--no-header",
            "-o", "addopts=",  # drop --cov from pyproject addopts (no pytest-cov)
        ]
        self.output.info("running upstream pytest: " + " ".join(cmd))
        res = subprocess.run(cmd, env=env, capture_output=True, timeout=900)
        out = (res.stdout or b"").decode(errors="replace")
        err = (res.stderr or b"").decode(errors="replace")
        self.output.info(out)
        if err.strip():
            self.output.info(err)
        # Parse the real summary line, e.g. "30 passed in 2.5s",
        # "28 passed, 2 failed, 1 skipped in 4.1s".
        passed = int(re.search(r"(\d+) passed", out).group(1)) if re.search(r"(\d+) passed", out) else 0
        failed = int(re.search(r"(\d+) failed", out).group(1)) if re.search(r"(\d+) failed", out) else 0
        skipped = int(re.search(r"(\d+) skipped", out).group(1)) if re.search(r"(\d+) skipped", out) else 0
        marker = {
            "status": "passed" if res.returncode == 0 else "failed",
            "framework": "pytest",
            "command": " ".join(cmd),
            "discovered": passed + failed + skipped,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if res.returncode != 0:
            raise ConanException(
                f"upstream pytest failed (exit {res.returncode}): "
                f"{passed} passed, {failed} failed, {skipped} skipped"
            )

    def test(self):
        pkg = self.dependencies["airthings-ble"].package_folder
        sp = self._find_site_packages(pkg)
        if not sp or not os.path.isdir(os.path.join(sp, "airthings_ble")):
            raise ConanException(f"airthings_ble missing under site-packages (pkg={pkg})")
        py = os.environ.get("PYTHONPATH", "")
        os.environ["PYTHONPATH"] = sp + ((":" + py) if py else "")

        # 1. Consumer API check (emits HMBS_TEST_PACKAGE_RESULT).
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_airthings_ble.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_airthings_ble.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{sp}'", env="conanrun")

        # 2. Upstream pytest suite (emits HMBS_UPSTREAM_TEST_RESULT).
        self._run_upstream_tests(sp)
