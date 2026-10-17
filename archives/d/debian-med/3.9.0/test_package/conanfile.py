#!/usr/bin/env python3
"""debian-med 3.9.0 test_package —— 纯数据包，无需编译。"""

import os
import sys

from conan import ConanFile


class BlendTestConan(ConanFile):
    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["debian-med"]
        package_folder = dep.package_folder
        script = os.path.join(self.source_folder, "test_blend.py")
        self.run(f"{sys.executable} {script} {package_folder}")
