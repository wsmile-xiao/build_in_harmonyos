#!/usr/bin/env python3
"""Runtime test for the packaged sipsak command."""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class SipsakTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        script = os.path.join(self.source_folder, "test_sipsak.sh")
        package_folder = self.dependencies["sipsak"].package_folder
        # HMBS injects SHELL=/bin/sh on the device: the HNP `bash` cannot
        # getcwd in the HMFS working directory and rejects `set -o pipefail`,
        # so run the POSIX script with the injected shell instead of bash.
        shell = os.environ.get("SHELL") or "sh"
        self.run(
            '"{}" "{}" "{}"'.format(shell, script, package_folder),
            env="conanrun",
        )
        # HMBS evidence marker: test_sipsak.sh runs 2 real assertions
        # (executable exists + `sipsak --version` prints 0.9.7) and exits
        # non-zero on any failure, so on success both passed. The numbers
        # are the actual test_package case count.
        marker = {
            "executed": True,
            "passed": True,
            "command": "sh test_sipsak.sh <package_folder>",
            "discovered": 2,
            "passedCount": 2,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        # HMBS upstream-test evidence: the main recipe runs the upstream
        # check_helper/check_md5 suites during build() and carries the real
        # summary into the package as res/upstream_test_summary.json. The
        # test_package stage always runs (even when a later preflight reuses
        # the cached binary and skips build()), so re-emit the marker here —
        # the numbers come from the true upstream test run on the device.
        summary_path = os.path.join(
            package_folder, "res", "upstream_test_summary.json"
        )
        if not os.path.isfile(summary_path):
            raise ConanException(
                "missing upstream test summary in package: " + summary_path
            )
        with open(summary_path, "r", encoding="utf-8") as handle:
            upstream = json.load(handle)
        if upstream.get("status") != "passed":
            raise ConanException(
                "upstream test summary status is not passed: "
                + json.dumps(upstream, ensure_ascii=False)
            )
        print(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        )
