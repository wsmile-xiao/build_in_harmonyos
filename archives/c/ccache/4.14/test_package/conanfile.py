#!/usr/bin/env python3
"""Conan test_package — ccache 4.14

Consumer test (R34): 模拟上层业务组件调用已安装的 ccache 公开 CLI
（bin/ccache），通过 test.sh 验证真实缓存语义（miss -> hit），
不使用库私有头文件或内部测试目录。
"""
import os

from conan import ConanFile


class CcacheTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'{bash} -ec "cd {self.build_folder} && sh {script}"', env="conanrun")