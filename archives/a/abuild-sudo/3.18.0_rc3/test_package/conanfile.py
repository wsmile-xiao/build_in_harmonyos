#!/usr/bin/env python3
"""Conan test_package — abuild-sudo 3.18.0_rc3 (executable).

Runs test.sh which executes the packaged abuild-sudo binary and asserts
its real behavior: the binary exists/executable and rejects non-whitelisted
invocations with a controlled error (group gate / subcommand validation).

After test.sh, re-emits HMBS_UPSTREAM_TEST_RESULT from the packaged
res/upstream_test_result.json (persisted by build() after it ran the 10
upstream ATF test programs through atf-shim.sh).  test_package runs on every
preflight even when conan skips a cached build() — "Already installed! (1 of
1)" — so the upstream evidence marker is always present in the run output.
If the packaged JSON is missing the package was produced without running the
upstream suite; that is an explicit failure, never a silent pass.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class AbuildSudoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution (CONFIG_SHELL from profile).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("{} test.sh".format(bash), env="conanrun")

        # Re-emit the upstream test result marker from the packaged JSON.
        dep = self.dependencies["abuild-sudo"]
        result_path = os.path.join(
            dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json not found in package ({}) — "
                "upstream tests did not run during build(); refusing to pass "
                "silently".format(result_path))
        with open(result_path, "r", encoding="utf-8") as f:
            upstream = json.load(f)
        print("HMBS_UPSTREAM_TEST_RESULT=" +
              json.dumps(upstream, ensure_ascii=False))

        # Re-emit the per-file breakdown (res/upstream_test_files.json) on
        # EVERY preflight so the log pinpoints which *_test file failed and
        # shows the failure tails — even when build() was skipped on a cached
        # binary.  The data comes from the same real device run that produced
        # the aggregate marker above.
        files_path = os.path.join(
            dep.package_folder, "res", "upstream_test_files.json")
        if os.path.isfile(files_path):
            with open(files_path, "r", encoding="utf-8") as f:
                files = json.load(f)
            print("HMBS_UPSTREAM_TEST_FILES=" +
                  json.dumps(files, ensure_ascii=False))
        else:
            raise ConanException(
                "upstream_test_files.json not found in package ({}) — "
                "per-file upstream evidence missing".format(files_path))
