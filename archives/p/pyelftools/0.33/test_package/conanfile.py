#!/usr/bin/env python3
"""pyelftools test_package — Conan L1 消费者测试 (R34 实质依赖被测包).

纯 Python 库：无 CMake/编译。test() 用 python 执行 test_pyelftools.py，
从被测包的 site-packages 导入 elftools 并做真实 ELF 解析 API 调用。
（同 packaging/26.3 test_package 先例）
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["pyelftools"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_pyelftools.py")
            # 沙箱 PATH 无 python3——绝对路径（同主配方 build() 教训）
            py = "/data/service/hnp/bin/python3" \
                if os.path.isfile("/data/service/hnp/bin/python3") \
                else sys.executable
            self.run(f'{py} "{test_script}" "{pkg}"', env="conanrun")
