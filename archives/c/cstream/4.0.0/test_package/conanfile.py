#!/usr/bin/env python3
"""test_package for cstream 4.0.0 — CLI binary functional checks."""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class CstreamTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross: skip run")
            return
        pkg = self.dependencies["cstream"].package_folder
        cstream = os.path.join(pkg, "bin", "cstream")
        # Case 1: version flag runs and reports 4.0.0.
        self.run('%s -V' % cstream, env="conanrun")
        # Case 2-3: pipe and file round-trip checks in test.sh.
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run('/bin/sh "%s" "%s"' % (test_sh, cstream), env="conanrun")
        marker = {
            "executed": True,
            "passed": True,
            "command": "cstream -V && sh test.sh (pipe + file round-trip)",
            "discovered": 3,
            "passedCount": 3,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
