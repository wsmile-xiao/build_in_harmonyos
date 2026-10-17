#!/usr/bin/env python3
"""zsxd 1.12.2 test_package —— 真实消费被测数据包。

用 Python zipfile 打开打包产物 data.solarus，逐条核对与上游 CMake glob 一致
的文件集合与关键文件内容；用 stub `solarus-run` 驱动 bin/zsxd，端到端验证
launcher 真实执行、quest 目录解析正确、追加参数透传。
"""

import os
import sys

from conan import ConanFile


class ZsxdTestConan(ConanFile):
    """test_package for zsxd —— 数据包完整性 + launcher 端到端验证。"""

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["zsxd"]
        package_folder = dep.package_folder
        script = os.path.join(self.source_folder, "test_zsxd.py")
        self.run(f"{sys.executable} {script} {package_folder}")
