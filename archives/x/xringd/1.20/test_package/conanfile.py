#!/usr/bin/env python3
"""xringd 1.20 消费者测试包：真执行包内 bin/xringd 与 bin/uartcount 的命令面。"""

import os
import sys

from conan import ConanFile


class XringdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        script = os.path.join(self.recipe_folder, "test_xringd.py")
        # 把包根交给脚本，由脚本自己拼 bin/... 与 res/...，并真跑子进程。
        self.run(
            '"{}" "{}" "{}"'.format(sys.executable, script, pkg),
            env="conanrun",
        )
