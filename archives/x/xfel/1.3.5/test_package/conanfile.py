#!/usr/bin/env python3
"""Consumer test for xfel 1.3.5 (test_type = "explicit").

断言全部放在 test.sh 中：它执行**已安装**的 bin/xfel 并对真实输出做校验，
因此验证的是包的公开使用面而不是一句 smoke print。调用点只负责拉起 bash
（OHOS 上 /system/bin/sh 无法执行 ELF，故显式走 CONFIG_SHELL/bash）。
"""
import os

from conan import ConanFile


class XfelTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" test.sh', env="conanrun")
