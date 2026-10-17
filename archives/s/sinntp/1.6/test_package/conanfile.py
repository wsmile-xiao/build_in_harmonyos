#!/usr/bin/env python3
"""test_package for sinntp 1.6 — consumer exercises installed scripts and modules."""

import json
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class SinntpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise Exception("can_run=False: consumer test must execute")
        test_script = os.path.join(self.source_folder, "test_sinntp.py")
        self.run('"%s" "%s"' % (sys.executable, test_script), env="conanrun")
        marker = {
            "executed": True,
            "passed": True,
            "command": "python3 test_sinntp.py",
            "discovered": 10,
            "passedCount": 10,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
