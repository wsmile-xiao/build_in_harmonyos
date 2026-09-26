#!/usr/bin/env python3
"""Conan test_package — ledmon 0.97 (Autotools, OHOS)

驱动 test_package/test_ledmon.sh 真实执行安装前缀下的 ledctl/ledmon 两个已签名
ELF，按退出码判定 5 项消费者行为断言（C1-C5）；conanrun 环境注入 LD_LIBRARY_PATH
（OHOS/musl 加载器忽略 DT_RUNPATH，不注入则 libudev.so.1 拒载）。
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class LedmonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # OHOS/musl 的加载器忽略 DT_RUNPATH，ledmon/ledctl 需要 eudev 的
        # libudev.so.1；conanrun.sh 把依赖的 lib 目录导出成 LD_LIBRARY_PATH，
        # 由 test() 的 env="conanrun" 注入（与 a52dec/aa3d 同法）。
        VirtualRunEnv(self).generate()

    def test(self):
        dep = self.dependencies["ledmon"]
        pkg = str(dep.package_folder)
        ledctl = os.path.join(pkg, "bin", "ledctl")
        ledmon = os.path.join(pkg, "bin", "ledmon")
        script = os.path.join(os.path.dirname(__file__), "test_ledmon.sh")
        self.run('sh "{}" "{}" "{}"'.format(script, ledctl, ledmon),
                 env="conanrun")
