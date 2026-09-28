#!/usr/bin/env python3
"""Conan test_package — wmget 0.6.1 CLI 契约冒烟（R34 真实产物校验）.

wmget 的 X11 DockApp 面无法无头运行（且 dock 服务器模式依赖的 SysV shm 在
OHOS PC 上运行期被 SIGSYS 拦截，见配方 notes）；按可无头运行的真实路径断言：
1. 产物 ELF 校验：magic + e_machine=EM_AARCH64(183)；
2. fork/exec 真跑 `wmget --version`，期望退出码 0（版本 banner）；
3. fork/exec 真跑 `wmget --help`，期望退出码 0（usage）。
参 sff/asmix 先例：消费者断言压产物 ELF/链接层 + CLI 契约，必不挂 UI 断言。
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class WmgetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # conanrun 环境：依赖 .so 的 libdirs 注入 LD_LIBRARY_PATH（子进程继承）
        VirtualRunEnv(self).generate()

    def build(self):
        bin_path = os.path.join(
            self.dependencies["wmget"].package_folder, "bin", "wmget"
        )
        self.output.info(f"wmget binary: {bin_path}")
        cc = os.environ.get("CC", "clang")
        self.run(
            f"{cc} -O2 -Wall test_wmget.c -o test_wmget "
            f"-DWMGET_BIN_PATH='\"{bin_path}\"'"
        )

    def test(self):
        self.run("./test_wmget", env="conanrun")
