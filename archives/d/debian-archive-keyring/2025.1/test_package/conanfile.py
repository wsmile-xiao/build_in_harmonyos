#!/usr/bin/env python3
"""debian-archive-keyring 2025.1 test_package —— 纯数据包，无需编译。"""

import os
import sys

from conan import ConanFile


class DebianArchiveKeyringTestConan(ConanFile):
    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["debian-archive-keyring"]
        package_folder = dep.package_folder
        data_dir = os.path.join(package_folder, "share", "keyrings")
        script = os.path.join(self.source_folder, "test_keyring.py")
        self.run(f"{sys.executable} {script} {data_dir} {package_folder}")
