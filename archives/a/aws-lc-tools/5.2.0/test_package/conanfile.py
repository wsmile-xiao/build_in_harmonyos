#!/usr/bin/env python3
"""Conan test_package for aws-lc-tools 5.2.0 (application package).

Consumer verification of the installed CLI tools:
  - runs test.sh under the conanrun env; the script invokes the installed
    bssl/openssl binaries for real operations (version, SHA-256 known-answer,
    rand length/alphabet, RSA keygen + parse + pubout) and prints the
    HMBS_TEST_PACKAGE_RESULT marker with its real case counters.
  - re-emits the HMBS_UPSTREAM_TEST_RESULT marker recorded by build() when
    the upstream gtest suite ran. Re-emission keeps the evidence present even
    when conan serves a cached package (build() does not re-run on cache hit);
    the JSON is produced from actual on-device test execution, never guessed.
"""
import json
import os

from conan import ConanFile


class AwsLcToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _dependency(self):
        for _require, dep in self.dependencies.items():
            if dep.ref.name == "aws-lc-tools":
                return dep
        return None

    def test(self):
        # Re-emit the upstream suite verdict captured during build() so the
        # marker survives package-cache hits. Project to the canonical 8-field
        # marker schema: the packaged JSON additionally carries per-invocation
        # details / exclusion audits which must not bloat the marker line.
        dep = self._dependency()
        if dep is not None and dep.package_folder:
            marker_file = os.path.join(str(dep.package_folder),
                                       "hmbs_upstream_result.json")
            if os.path.isfile(marker_file):
                try:
                    with open(marker_file, encoding="utf-8") as fh:
                        data = json.load(fh)
                    marker = {k: data.get(k) for k in
                              ("status", "framework", "command", "discovered",
                               "executed", "passed", "failed", "skipped")}
                    self.output.info(
                        "HMBS_UPSTREAM_TEST_RESULT="
                        + json.dumps(marker, ensure_ascii=False))
                except (OSError, ValueError):
                    pass

        # OHOS: /system/bin/sh cannot execute ELF binaries directly; run via
        # bash (hmbs/CONFIG_SHELL provides it on the device).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
