#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ink 0.5.3 消费者测试（conan test_package）

ink 是命令行工具（无 C/C++ 消费 API），test() 通过 bash 包装执行 test.sh：
运行 ink -v，验证二进制可执行且成功动态链接 libinklevel（-v 会调用
libinklevel 的 get_version_string()）。不用 ctest 中转：CI 的 test() 实际
执行检查（L0d / PF3）要求 test_package 内显式调用 self.run()。
"""

import os

from conan import ConanFile


class InkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 不能直接执行 ELF，用 bash 包装
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
