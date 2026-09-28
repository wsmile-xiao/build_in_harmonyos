#!/usr/bin/env python3
"""scrub test_package — application 型消费者测试。

test_type=explicit；被测物 = self.tested_reference_str 解析出的包内
bin/scrub（application 包无库可链）。test.sh 真跑该二进制：
--version 断言、fillff 擦写后逐字节校验、--dry-run 不落盘、默认
pattern + -r 擦写后 unlink（R34：实质执行被测物，非空壳）。
"""
import os

from conan import ConanFile


class ScrubTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{script}"', env="conanrun")
