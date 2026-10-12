#!/usr/bin/env python3
"""Conan test_package — bart-view 0.3.00 consumer test (R34).

bart-view 交付 view / cfl2png 两个可执行文件（application 类型，无库 API）。
L1 测试以消费者视角实际执行被测包二进制（非空壳）：

  1. 编译 test.c（L0c 载体）；
  2. 断言 bin/view、bin/cfl2png 存在且可执行；
  3. 运行鸿蒙特有测试 test_cfl2png.py：
     - cfl2png 端到端 cfl→png 转换（合成数据集，校验 PNG 签名/尺寸/数据依赖/确定性）；
     - view 在无 DISPLAY 下加载 GTK3 依赖栈（无缺库报错）。

CI 通过 `conan create` 自动调用本 test()（L1）。
"""
import os

from conan import ConanFile


class BartViewTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_bart_view")
        self.run(f"{cc} {src} -o {out}")

    def test(self):
        bindir = os.path.join(
            self.dependencies["bart-view"].package_folder, "bin")
        view = os.path.join(bindir, "view")
        cfl2png = os.path.join(bindir, "cfl2png")
        self.run(f"test -x {view}")
        self.run(f"test -x {cfl2png}")
        # 鸿蒙特有测试：cfl2png 端到端转换 + view GTK3 依赖栈加载
        script = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "test_cfl2png.py")
        self.run(f"python3 {script} {bindir}", env="conanrun")
        self.output.info("bart-view consumer test passed")
