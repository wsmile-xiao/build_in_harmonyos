#!/usr/bin/env python3
"""test_package — bsdgames-nonfree 2.17 (rogue).

R34: 实质验证被测包功能（非空壳打印）：
  调用独立测试脚本 test_rogue.sh 执行：
  1. rogue 二进制存在且可执行
  2. 运行 rogue（stdin 输入名字 + quit），断言输出包含启动横幅 "Hey!"
  3. 断言退出码为 0
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class BsdgamesnonfreeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["bsdgames-nonfree"]
            rogue = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "rogue")
            script = os.path.join(self.source_folder, "test_rogue.sh")

            # 独立测试脚本真实执行 rogue：启动横幅 "Hey!" + 退出码 0
            self.run(f'bash "{script}" "{rogue}"', env="conanrun")
