#!/usr/bin/env python3
"""ieee-data 20260625 test_package —— 纯数据包，无需编译。

验证逻辑全部放在独立的 test_ieee_data.py 里，本文件只负责：
  1) 通过 dependencies 拿到被测算包的真实 package_folder；
  2) 用当前 Python 解释器（Conan 自身的解释器）执行验证脚本。
"""

import os
import sys

from conan import ConanFile


class IeeeDataTestConan(ConanFile):
    # 纯数据包：无编译器、无 settings、无 build 步骤。
    # test_type 保持默认（在 conan create / conan test 中立即执行）。

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["ieee-data"]
        package_folder = dep.package_folder
        data_dir = os.path.join(package_folder, "share", "ieee-data")

        script = os.path.join(self.source_folder, "test_ieee_data.py")
        self.run(f"{sys.executable} {script} {data_dir} {package_folder}")
