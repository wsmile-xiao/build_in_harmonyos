#!/usr/bin/env python3
"""Conan L1 test_package — ngs 0.2.17 (application)

被测包只产出可执行文件（无可链接库），因此测试以 Conan runenv 真实执行包内
ngs 二进制，由同目录 test.sh 承载具体断言（版本自证、NGS_PATH 加载、
表达式求值与插值，以及 ngs_smoke.ngs 的依赖链功能断言）。
"""
import os

from conan import ConanFile


class NgsTestConan(ConanFile):
    name = "ngs-test-package"
    version = "0.0.0"
    description = "L1 test: run the packaged ngs interpreter end to end"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: 真实执行被测包安装的 ngs 二进制（application 包没有可链接库）
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test.sh")
        # 两个路径都必须带引号：CONFIG_SHELL 或包缓存路径含空格时裸展开会断裂
        self.run(f"\"{bash}\" \"{script}\"", env="conanrun")
