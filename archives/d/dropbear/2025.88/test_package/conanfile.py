#!/usr/bin/env python3
"""Conan test_package for dropbear — 真实执行的消费者冒烟测试。

在设备上直接运行被测产物（env="conanrun"）：
  1. 四个可执行文件存在性；
  2. dropbearkey 生成 ed25519 密钥并导出公钥；
  3. dropbearconvert dropbear→openssh→dropbear 双向转换后与原私钥逐字节一致；
  4. dropbear/dropbearkey/dbclient 的 usage/帮助路径退出码为 0。

脚本自身定义在 test_package 源目录，全部输出与临时文件写在 build_folder
（layout 已分离），不污染包源目录。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class DropbearTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder="test_package")

    def test(self):
        package_folder = self.dependencies["dropbear"].package_folder
        if not can_run(self):
            # 交叉编译上下文：仅核对打包产物存在性。
            for sub in ("bin", "sbin"):
                for name in ("dropbear", "dropbearkey", "dropbearconvert", "dbclient"):
                    if not os.path.isfile(os.path.join(package_folder, sub, name)):
                        raise ConanException(f"packaged command missing: {sub}/{name}")
            self.output.info("cross-compile context: packaged binaries exist")
            return
        script = os.path.join(self.recipe_folder, "test_dropbear.sh")
        self.run(
            f'sh "{script}" "{package_folder}" "{self.build_folder}"',
            env="conanrun",
        )
