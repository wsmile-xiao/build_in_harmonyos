#!/usr/bin/env python3
"""test_package for quicklisp/20150128 — 消费者视角 L1 测试。

R34：test() 真实执行被测物，而不是只做文件存在性检查——
制品仓内的 ECL 24.5.10（Common Lisp 实现，OHOS/armv8）会把安装后的
quicklisp.lisp 实际 (load ...) 起来，断言 quickstart 横幅与版本号
（2015-01-28）以及入口函数 quicklisp-quickstart:install 存在。
这正是上游 README.txt 给出的唯一使用入口。

ecl 仅作为**测试用**依赖（语言运行时），不进入 quicklisp 的 requires()：
quicklisp 本体只是一个与架构无关的启动文件。
"""
import os

from conan import ConanFile


class QuicklispTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Common Lisp 实现（语言运行时）——仅测试用，用于真实加载被测启动文件
        self.requires("ecl/24.5.10")

    def test(self):
        dep = self.dependencies["quicklisp"]
        ecl = self.dependencies["ecl"]
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_sh}" "{dep.package_folder}" "{ecl.package_folder}"',
                 env="conanrun")
