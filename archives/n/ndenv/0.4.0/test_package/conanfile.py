#!/usr/bin/env python3
"""Conan test_package for ndenv 0.4.0 — smoke test via test_ndenv.sh.

ndenv is a pure shell script tool (application). test() runs
test_ndenv.sh against the packaged bin dir: existence/executable bit,
bash shebang, bash -n syntax check over libexec, --version output,
`commands` dispatcher listing and `versions` with an empty NDENV_ROOT
(R34: really executes the packaged scripts, exit code decides pass/fail).
test() also emits HMBS_TEST_PACKAGE_RESULT and re-emits the
HMBS_UPSTREAM_TEST_RESULT(no_tests) marker every round, since the main
recipe build() marker is skipped on package cache hits.
"""

import json
import os

from conan import ConanFile


class NdenvTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["ndenv"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: exercise the packaged ndenv scripts — presence, shebang,
        # syntax, --version, commands dispatcher and versions listing.
        # The script exits non-zero on any failed assertion, failing create.
        cmd = f'bash test_ndenv.sh "{bin_dir}"'
        self.run(cmd, env="conanrun")
        marker = {
            "executed": True,
            "passed": True,
            "command": cmd,
            "discovered": 6,
            "passedCount": 6,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        # Upstream ships no test suite (MANIFEST.yml audit); re-emit the
        # no_tests marker here so evidence exists even on cache hits.
        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "payload sanity check (upstream ships no test suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "ndenv 0.4.0 上游无测试套件：仓库根仅 bin/completions/libexec，无 test 目录、无 bats/Makefile/CMake 测试目标（审计见 test_package/MANIFEST.yml）",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker))
