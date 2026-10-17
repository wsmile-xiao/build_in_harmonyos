#!/usr/bin/env python3
"""wm-icons 0.4.0 test_package —— 纯资源包，无需编译。"""

import os
import sys

from conan import ConanFile


class WmIconsTestConan(ConanFile):
    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["wm-icons"]
        package_folder = dep.package_folder
        data_dir = os.path.join(package_folder, "share", "wm-icons")
        script = os.path.join(self.source_folder, "test_wm_icons.py")
        self.run(f"{sys.executable} {script} {data_dir} {package_folder}")
