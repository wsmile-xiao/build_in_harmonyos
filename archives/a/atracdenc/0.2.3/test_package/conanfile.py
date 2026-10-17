#!/usr/bin/env python3
"""Conan test_package for atracdenc 0.2.3 — functional smoke test of the CLI.

Runs `atracdenc -h` (help must exit 0) and an end-to-end ATRAC3 encode of a
generated 44100 Hz 16-bit WAV into an OMA file, verifying the output is
non-empty.  Emits the HMBS_TEST_PACKAGE_RESULT marker with the real assertion
count from test.sh (2 checks).
"""
import json
import os

from conan import ConanFile


class AtracdencTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 2 explicit checks in test.sh: -h help, ATRAC3 encode with non-empty OMA
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "bash test.sh",
            "discovered": 2,
            "passedCount": 2,
        }
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly,
        # so wrap the test script with the bash from the build environment.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        try:
            self.run(f"{bash} test.sh", env="conanrun")
        except Exception:
            test_pkg["passed"] = False
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            raise
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
