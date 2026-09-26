#!/usr/bin/env python3
"""Conan test_package for verovio 6.2.1 — functional smoke test of the CLI.

Runs test.sh, which performs 4 checks against the installed CLI:
  1. `verovio --version` prints a Verovio banner,
  2. renders a real MEI score to SVG (exit 0),
  3. verifies the SVG is non-empty,
  4. verifies the SVG has a valid <svg> root element.

test.sh writes a machine-readable result JSON whose `discovered`/`passed` come
from its own control flow (single deterministic source), and the
HMBS_TEST_PACKAGE_RESULT marker is built from those real values.
"""
import json
import os

from conan import ConanFile


class VerovioTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_pkg = {
            "executed": True,
            "passed": False,
            "command": "bash test.sh",
            "discovered": 0,
            "passedCount": 0,
        }
        # Point the CLI at the installed resource data (SMuFL matrices etc.).
        res_dir = os.path.join(
            self.dependencies["verovio"].package_folder, "share", "verovio")
        # Result file the script writes (single source of the counts).
        result_json = os.path.join(self.build_folder, "test_package_result.json")
        # The test script is POSIX-sh compatible; run it with the harness shell
        # ($CONFIG_SHELL, /bin/sh on the device) so no bash dependency exists.
        bash = os.environ.get("CONFIG_SHELL", "/bin/sh")
        cmd = f"VEROVIO_RESOURCE_DIR={res_dir} HMBS_TP_RESULT={result_json} {bash} test.sh"
        rc = 1
        try:
            self.run(cmd, env="conanrun")
            rc = 0
        except Exception as exc:  # noqa: BLE001 - surface real device failure
            self.output.info(f"test.sh raised: {exc}")
            rc = 1

        # Read the real counts written by test.sh (deterministic single source).
        if os.path.exists(result_json):
            try:
                with open(result_json, encoding="utf-8") as fh:
                    data = json.load(fh)
                test_pkg["discovered"] = int(data.get("discovered", 0))
                test_pkg["passedCount"] = int(data.get("passed", 0))
            except Exception as exc:  # noqa: BLE001
                self.output.info(f"could not parse result json {result_json}: {exc}")

        test_pkg["passed"] = (rc == 0) and (
            test_pkg["passedCount"] == test_pkg["discovered"]
        )
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
        if not test_pkg["passed"]:
            raise SystemExit(1)
