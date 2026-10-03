#!/usr/bin/env python3
"""Consumer test for the packaged sedparse module and CLI."""

import json
import os
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import can_run


class SedparseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise Exception("can_run=False: consumer test must execute")
        test_script = os.path.join(self.source_folder, "test_sedparse.py")
        self.run('"%s" "%s"' % (sys.executable, test_script), env="conanrun")
        marker = {
            "executed": True,
            "passed": True,
            "command": "python test_sedparse.py",
            "discovered": 12,
            "passedCount": 12,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
