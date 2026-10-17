#!/usr/bin/env python3
"""test_package — john-jumbo 1.9.0 消费者测试（Makefile.legacy 构建产物）。

test() 以 CONFIG_SHELL/PATH 探测到的 bash 执行 test.sh（19 条具名用例，
任一失败 exit 1）。
"""

import os
import shutil

from conan import ConanFile


class JohnJumboTestConan(ConanFile):
    """test_package for john-jumbo -- runs test.sh which exercises the packaged john binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def configure(self):
        # 同主配方：OHOS settings.yml 为 OHOS 定义 version 子设置且无默认值，
        # 未声明 os.version 时 test_package 自身 package_id 校验同样报
        # "Invalid: 'settings.os.version' value not defined"（知识库
        # DRAFT-glpk-4.65-ohos-conan-os-version-rm-safe），rm_safe 移除之。
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # bash 解析顺序：CONFIG_SHELL（profile/CI buildenv 显式注入）→ PATH 探测
        # （Linux CI worker）→ /data/service/hnp/bin/bash（OHOS 真机兜底，该路径
        # 通常不在 PATH，保留写死值仅作最后回退）。
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(f"{bash} test.sh", env="conanrun")
