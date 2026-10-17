#!/usr/bin/env python3
"""test_package for sc-im 0.8.5 — 消费者视角的 CLI 功能与安装树断言（7 项）。

test.sh 由 bash 显式驱动（OHOS 上 /system/bin/sh 是 toybox，官方惯例统一用
/data/service/hnp/bin/bash 包一层执行），二进制路径以**绝对路径**传入（不依赖
conanrun 的 PATH 解析），工作目录写在 build 目录内（/tmp 只读）。
"""
import os

from conan import ConanFile


class ScImTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        pkg = self.dependencies["sc-im"].package_folder
        work = os.path.join(self.build_folder, "scim-consumer-work")
        os.makedirs(work, exist_ok=True)
        # HOME 钉进工作目录：sc-im 会读写 $HOME/.config/scimrc、$HOME/.cache，
        # 不能落到调用者真实 HOME（上游测试沙箱同口径）。
        self.run(f'HOME="{work}/home" {bash} test.sh "{pkg}" "{work}"',
                 env="conanrun")
