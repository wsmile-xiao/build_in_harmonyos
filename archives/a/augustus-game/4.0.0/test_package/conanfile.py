#!/usr/bin/env python3
"""Consumer test for augustus-game 4.0.0 (application).

图形游戏在无显示/无音频设备环境无法进入主循环；包内二进制经补丁 0004
支持无头 --version（SDL 初始化前打印版本并以 0 退出），用它做冒烟验证。
具体断言逻辑在 test.sh（CI L0c 门禁要求 test_package 下有测试源文件）。
"""
import os

from conan import ConanFile


class AugustusgameTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os not in ("Linux", "OHOS"):
            return
        pkg = self.dependencies["augustus-game"].package_folder
        exe = os.path.join(pkg, "bin", "augustus")
        assert os.path.isfile(exe), f"augustus binary not found at {exe}"
        # test.sh 使用 POSIX shell 语法，避免绑定某台真机的 bash 安装路径。
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run(f'{shell} "{os.path.join(self.source_folder, "test.sh")}" "{exe}"',
                 env="conanrun")
