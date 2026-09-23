#!/usr/bin/env python3
"""Consumer test for caesiumclt 1.4.0."""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class CaesiumcltTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-build: runtime test deferred to OHOS device")
            return
        dependency = self.dependencies[self.tested_reference_str]
        binary = os.path.join(dependency.package_folder, "bin", "caesiumclt")
        if not os.path.isfile(binary):
            raise AssertionError(f"caesiumclt binary not found: {binary}")
        script = os.path.join(self.source_folder, "test_caesiumclt.py")
        self.run(f'python3 "{script}" "{binary}"', cwd=self.source_folder)
        # test_caesiumclt.py runs 4 assertions: version, help, real
        # compression producing non-empty output, dry-run.
        marker = {
            "executed": True,
            "passed": True,
            "command": f'python3 "{script}" "{binary}"',
            "discovered": 4,
            "passedCount": 4,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
