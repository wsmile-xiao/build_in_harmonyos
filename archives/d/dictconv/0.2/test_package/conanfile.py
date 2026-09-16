#!/usr/bin/env python3
"""Conan test_package — dictconv 0.2（消费者视角验证）。

上游 dictconv 0.2 没有测试套件（无 make check / ctest / tests 目录），因此这里
用 test.sh 做消费者测试：真实调用已安装的 dictconv 可执行文件，逐项校验
GNU 长选项、三种输出格式的字节级结果与错误路径退出码（详见 test.sh 顶部说明）。
"""
import os

from conan import ConanFile


class DictconvTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 执行 ELF 二进制不稳定，统一用 hnp 自带 bash 包装
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
