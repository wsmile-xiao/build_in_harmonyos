#!/usr/bin/env python3
"""Conan test_package for tofuenv 1.0.7.1.

tofuenv is a pure bash shell script tool (no compiled binary).
L1 test: verify 'tofuenv --version' runs successfully.
--version only needs bash + awk (no jq dependency).
"""
import os

from conan import ConanFile


class TofuenvTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # bash path: OHOS uses /data/service/hnp/bin/bash; Linux/CI uses system bash
        bash = os.environ.get("CONFIG_SHELL")
        if not bash:
            hnp_bash = "/data/service/hnp/bin/bash"
            bash = hnp_bash if os.path.exists(hnp_bash) else "bash"
        self.run(f"{bash} test.sh", env="conanrun")
