#!/usr/bin/env python3
"""Consumer test for herdr: version check, server lifecycle, workspace API."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class HerdrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-build: runtime test deferred to OHOS/shadow CI")
            return

        dependency = self.dependencies[self.tested_reference_str]
        binary = os.path.join(dependency.package_folder, "bin", "herdr")
        script = os.path.join(self.source_folder, "test_herdr.py")
        self.run(f'python3 "{script}" "{binary}"', cwd=self.source_folder)