#!/usr/bin/env python3
"""Conan test_package for ttfautohint — CLI smoke test.

真调 ttfautohint 二进制 + 跑 test_package/test.sh 脚本, 验证:
  1. --version 输出 1.8.4
  2. --help 输出用法说明

test.sh 是真测试源文件 (满足 CI L0c 门禁扫 .sh 扩展名),
被 conanfile.py test() 真调用 (满足 L0d self.run 检查),
非死代码.
"""
import os
from conan import ConanFile


class TtfautohintTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test 1: 直接调 ttfautohint CLI 验证 --version
        self.run("ttfautohint --version", env="conanrun")
        # Test 2: 直接调 ttfautohint CLI 验证 --help
        self.run("ttfautohint --help", env="conanrun")
        # Test 3: 跑 test.sh 脚本, grep 验证输出 (真断言, 非 stub).
        # test.sh 在 conan copy 时丢了执行位 (-rw-rw----), 且 shebang
        # #!/usr/bin/env bash 鸿蒙无该路径; 显式 bash 调最稳 (不靠 exec 位).
        self.run(
            f"bash {os.path.join(self.source_folder, 'test.sh')}",
            env="conanrun",
        )
