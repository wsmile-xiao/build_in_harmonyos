#!/usr/bin/env python3
"""Conan test_package for rl-accel 0.9.1 — 消费者视角验证（R34 真实 API + 鸿蒙专项）。

以**已打包**的扩展为消费者：
  1. test_rl_accel.py —— import ``_rl_accel`` 并真实调用其全部公开函数，
     与纯 Python 参考实现逐值比对（calcChecksum/add32/hex32/escapePDF/
     fp_str/asciiBase85*/unicode2T1/instanceStringWidth*/sameFrag）。
  2. test_rl_accel_ohos.py —— 鸿蒙专项测试：产物 ELF 为 AArch64-linux-ohos
     且带 ``.codesign`` 段（OHOS 沙箱 dlopen 前提）；并在 musl 运行期复算
     与 libc 强弱相关的路径（printf 数值格式化、Ascii85 位运算）确认无
     平台偏差。

env="conanrun" 注入是必需的：包侧 package_info() 用 runenv_info 声明了
PYTHONPATH，裸 subprocess 会丢失该注入。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class RlAccelTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["rl-accel"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        exts = [f for f in os.listdir(site)
                if f.startswith("_rl_accel") and f.endswith(".so")]
        if not exts:
            raise ConanException(
                f"rl-accel payload incomplete (_rl_accel*.so missing): {site}")
        so_path = os.path.join(site, sorted(exts)[0])

        here = os.path.dirname(__file__)
        consumer = os.path.join(here, "test_rl_accel.py")
        ohos_test = os.path.join(here, "test_rl_accel_ohos.py")
        for script in (consumer, ohos_test):
            if not os.path.isfile(script):
                raise ConanException(f"{os.path.basename(script)} missing: {script}")

        # 1) 消费者真实 API（R34）
        self.run(f'python3 "{consumer}" "{site}"', env="conanrun")
        # 2) 鸿蒙专项
        self.run(f'python3 "{ohos_test}" "{so_path}"', env="conanrun")
