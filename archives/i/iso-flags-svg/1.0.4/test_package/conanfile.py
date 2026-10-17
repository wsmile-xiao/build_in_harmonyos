#!/usr/bin/env python3
"""iso-flags-svg 1.0.4 test_package —— 纯数据包，无需编译。

验证逻辑全部放在独立的 test_iso_flags.py 里，本文件只负责：
  1) 通过 dependencies 拿到被测算包的真实 package_folder；
  2) 用当前 Python 解释器（Conan 自身的解释器）执行验证脚本。
"""

import os
import sys

from conan import ConanFile


class IsoFlagsSvgTestConan(ConanFile):
    # 纯数据包：无编译器、无 settings、无 build 步骤。

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["iso-flags-svg"]
        package_folder = dep.package_folder
        data_dir = os.path.join(package_folder, "share", "iso-flags-svg")

        script = os.path.join(self.source_folder, "test_iso_flags.py")
        self.run(f"{sys.executable} {script} {data_dir} {package_folder}")
