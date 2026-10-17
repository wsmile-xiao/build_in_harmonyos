#!/usr/bin/env python3
"""Conan test_package — hashrat 1.25 (CLI application)

hashrat 是命令行工具，无公开库 API；L1 冒烟测试直接执行安装后的
bin/hashrat，按输出内容断言（上游语义：-version 与哈希管道退出码为 1，
不能依赖 rc==0）：
  - `hashrat -version` 输出必须为 `version: 1.25`
  - `echo -n <向量输入> | hashrat -sha256` 输出必须为已知向量
    c7fadad016311a935a56dcdfb585cf5a4781073f7da13afa22177796e566434f
"""
import os

from conan import ConanFile


class HashratTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        exe = os.path.join(self.dependencies["hashrat"].package_folder, "bin", "hashrat")
        if not os.path.exists(exe):
            raise SystemExit(f"hashrat binary missing: {exe}")

        # 物理测试源文件（L0c 门禁要求）：test_hashrat.sh 实际执行安装产物
        # bin/hashrat，断言 -version 输出、SHA-256 已知向量与退出码语义。
        script = os.path.join(self.recipe_folder, "test_hashrat.sh")
        if not os.path.exists(script):
            raise SystemExit(f"test source missing: {script}")
        self.run(
            f"bash {script} {exe}",
            env="conanrun",
        )
