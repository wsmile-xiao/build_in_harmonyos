#!/usr/bin/env python3
"""Conan test_package — nInvaders 0.1.1 terminal game smoke test.

nInvaders is a ncurses terminal game (application), not a library. The test
really executes the packaged binary via its documented CLI path (unknown
option -> version + usage banner, exit code 1) and asserts the banner text.

Upstream ships no automated test suite; the HMBS_UPSTREAM_TEST_RESULT marker
is re-emitted here with status=no_tests so the evidence gate always sees it.
"""
import json
import os

from conan import ConanFile


def _bash():
    """Use CONFIG_SHELL from environment; fall back to /bin/sh on OHOS."""
    return os.environ.get("CONFIG_SHELL", "/bin/sh")


class NInvadersTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(
            self.dependencies["ninvaders"].package_folder, "bin", "nInvaders"
        )
        self.output.info(f"Checking binary: {bin_path}")
        assert os.path.isfile(bin_path), f"nInvaders binary not found at {bin_path}"

        # Real execution: run the packaged binary through its CLI contract.
        test_cmd = f"'{_bash()}' '{self.source_folder}/test.sh' '{bin_path}'"
        # discovered = test.sh 中的断言数（版本横幅 + Usage 行）
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": test_cmd,
            "discovered": 2,
            "passedCount": 2,
        }
        try:
            self.run(test_cmd, env="conanrun")
        except Exception as exc:
            test_pkg["passed"] = False
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
            )
            raise

        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
        )

        # Upstream test marker: ninvaders 0.1.1 has no test suite (audit in
        # test_package/MANIFEST.yml: Makefile has no check target, no tests/
        # directory in the release tarball).
        upstream = {
            "status": "no_tests",
            "framework": "none",
            "command": "make -n (upstream Makefile has no check/test target)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "ninvaders 0.1.1 upstream has no test suite: release tarball "
                "contains only game sources + Makefile, Makefile defines only "
                "all/clean targets, no tests/ directory or test framework"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        )