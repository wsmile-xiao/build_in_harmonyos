#!/usr/bin/env python3
"""test_package for duff 0.5.2（上游 0.5.2）— 消费者端到端验证。

duff 是命令行工具，因此 L1 测试不带 C/C++ 消费者代码，而是真实执行包内安装
的 `duff` 二进制（R34：测试必须实质调用被测包）：
  * 真实重复文件检测 / 摘要算法选择 / excess 模式等上游 CLI 行为；
  * OHOS 平台契约：AArch64 ELF、动态依赖 gettext 提供的 libintl.so.8、
    gettext 译文在包内 LOCALEDIR 下实际生效（证明 NLS 适配真实可用）。

具体断言见 test_duff.sh（脚本以 conanrun 环境执行，PATH 含 <pkg>/bin，
LD_LIBRARY_PATH 含 libintl 所在 lib 目录）。
"""
import os

from conan import ConanFile


class DuffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 不能执行 ELF 二进制，用 bash 包装。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_duff.sh", env="conanrun")
