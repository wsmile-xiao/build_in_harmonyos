#!/usr/bin/env python3
"""Consumer test for bottom — verifies the btm binary runs and reports version."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class BottomTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-build: runtime test deferred to OHOS/shadow CI")
            return
        dependency = self.dependencies[self.tested_reference_str]
        binary = os.path.join(dependency.package_folder, "bin", "btm")
        if not os.path.isfile(binary):
            raise AssertionError(f"btm binary not found at {binary}")
        script = os.path.join(self.source_folder, "test_btm.py")
        self.run(f'python3 "{script}" "{binary}"', env="conanrun")
