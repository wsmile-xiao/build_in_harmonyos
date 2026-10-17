#!/usr/bin/env python3
"""Conan test_package for ld2410-ble 0.2.0 — pure-Python consumer verification.

Runs three layers against the package produced by THIS recipe:

  1. ``test_ld2410_ble.py`` — consumer API check over the real LD2410B/C wire
     protocol (frame parsing, target-state flags, engineering-mode energy
     gates, callbacks, split-frame buffering).  Emits
     ``HMBS_TEST_PACKAGE_RESULT``.  No BLE hardware required.
  2. ``test_ld2410_ble_ohos.py`` — HarmonyOS-specific platform contract check
     (OHOS runtime identity, little-endian aarch64 decoding, pure-Python /
     no native extension, dependency import completeness, and the bleak
     backend gap on ``platform.system() == "HarmonyOS"``).  Emits
     ``HMBS_OHOS_TEST_RESULT``.
  3. The vendored upstream pytest suite (``tests/``, copied verbatim from the
     upstream GitHub tag archive — PyPI's sdist ships no tests/).  Emits
     ``HMBS_UPSTREAM_TEST_RESULT`` with the real pytest counts.

PYTHONPATH injection: ``ld2410_ble`` is pure Python and its runtime deps
(bleak, bleak-retry-connector, async-timeout) were pip-installed into the very
same site-packages by the recipe's ``build()``, so the package's own
site-packages is self-sufficient — no external env vars are required (R33).
The interpreter is ``sys.executable`` (the Conan-managed Python) rather than a
bare ``python3`` from PATH, mirroring the recipe's ``build()``.
"""
import json
import os
import re
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException


class Ld2410BleTestConan(ConanFile):
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
        """Run the vendored upstream pytest suite; emit HMBS_UPSTREAM_TEST_RESULT."""
        tests_dir = os.path.join(os.path.dirname(__file__), "tests")
        if not os.path.isdir(tests_dir):
            raise ConanException(
                f"upstream tests/ not vendored into test_package: {tests_dir}"
            )
        env = dict(os.environ)
        env["PYTHONPATH"] = sp
        python = sys.executable
        # pytest is not a runtime dep of the library; fetch it from the mirror
        # if the CI image does not provide it.
        try:
            probe = subprocess.run(
                [python, "-m", "pytest", "--version"],
                env=env, capture_output=True, timeout=60,
            )
            if probe.returncode != 0:
                raise OSError("pytest unavailable")
        except Exception:
            self.output.info("installing pytest from the configured mirror")
            subprocess.run(
                [python, "-m", "pip", "install", "pytest"],
                env=env, capture_output=True, timeout=300,
            )
        cmd = [
            python, "-m", "pytest", tests_dir, "-q", "--no-header",
            "-o", "addopts=",  # drop --cov/pythonpath from the upstream pyproject
            "-p", "no:cacheprovider",
        ]
        self.output.info("running upstream pytest: " + " ".join(cmd))
        res = subprocess.run(cmd, env=env, capture_output=True, timeout=900)
        out = (res.stdout or b"").decode(errors="replace")
        err = (res.stderr or b"").decode(errors="replace")
        self.output.info(out)
        if err.strip():
            self.output.info(err)
        passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", out)) else 0
        failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", out)) else 0
        skipped = int(m.group(1)) if (m := re.search(r"(\d+) skipped", out)) else 0
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
        pkg = self.dependencies["ld2410-ble"].package_folder
        sp = self._find_site_packages(pkg)
        if not sp or not os.path.isdir(os.path.join(sp, "ld2410_ble")):
            raise ConanException(
                f"ld2410_ble missing under site-packages (pkg={pkg})"
            )
        py = os.environ.get("PYTHONPATH", "")
        os.environ["PYTHONPATH"] = sp + ((":" + py) if py else "")
        self.output.info(f"ld2410-ble consumer site-packages: {sp}")

        here = os.path.dirname(__file__)
        python = sys.executable

        # 1. Consumer API check (emits HMBS_TEST_PACKAGE_RESULT).
        consumer = os.path.join(here, "test_ld2410_ble.py")
        if not os.path.isfile(consumer):
            raise ConanException(f"consumer test source missing: {consumer}")
        self.run(f"'{python}' '{consumer}' '{sp}'", env="conanrun")

        # 2. HarmonyOS-specific platform contract check (emits HMBS_OHOS_TEST_RESULT).
        ohos = os.path.join(here, "test_ld2410_ble_ohos.py")
        if not os.path.isfile(ohos):
            raise ConanException(f"HarmonyOS test source missing: {ohos}")
        self.run(f"'{python}' '{ohos}' '{sp}'", env="conanrun")

        # 3. Upstream pytest suite (emits HMBS_UPSTREAM_TEST_RESULT).
        self._run_upstream_tests(sp)
