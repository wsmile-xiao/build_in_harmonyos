#!/usr/bin/env python3
"""test_package — xclicker 消费者视角验证（OHOS 平台）。

xclicker 是可执行程序（非库），因此验证方式为：
  1) 断言包内产出 bin/xclicker 存在；
  2) 执行 test.sh —— 鸿蒙特有平台检查（AArch64 ELF / OHOS musl 解释器 /
     .codesign 签名段 / NEEDED 链接 OHOS 适配的 GTK+X11 栈）+ 真实运行
     `xclicker --help`（加载全部动态依赖后退出 0）。
"""
import os

from conan import ConanFile


class XClickerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["xclicker"].package_folder
        binary = os.path.join(pkg, "bin", "xclicker")
        if not os.path.isfile(binary):
            raise Exception(f"xclicker binary missing in package: {binary}")
        self.output.info(f"xclicker binary: {binary}")
        # OHOS: /system/bin/sh（mksh）不能直接跑 ELF，用 bash 承载脚本
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
        self.output.info("xclicker test_package PASS")
