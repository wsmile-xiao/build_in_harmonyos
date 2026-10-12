# -*- coding: utf-8 -*-
"""jomon test_package — 消费者视角验证（R34：执行被测包的真实二进制，非空壳）

jomon 是应用而非库，消费者视角 = 安装后能运行且行为与上游一致：
  --version                版本宏由构建注入（JOMON_VERSION -> config.mk）
  --help                   CLI 选项表可打印
  -ddd -f "tcp or icmp"    离线把 tcpdump 语法编译为 BPF 并反汇编输出。
                           上游 main.c 在 print_bpf_and_exit() 处直接退出，
                           早于任何网络接口初始化，因此无需 root 与网卡；
                           该路径覆盖 re2c 生成的词法器与 BPF 编译器。

断言逻辑集中在测试源文件 test.sh（CI L0c/L0e 与本仓 PF3 要求）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class JomonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: 跳过运行（本包为应用，仅验证可被消费）")
            return

        dep = self.dependencies[self.tested_reference_str]
        jomon = os.path.join(dep.package_folder, "bin", "jomon")

        # test.sh 是测试源文件，可能位于 recipe/build/source 三者之一
        script = ""
        for folder in (self.recipe_folder, self.build_folder, self.source_folder):
            candidate = os.path.join(folder, "test.sh")
            if os.path.exists(candidate):
                script = candidate
                break
        if not script:
            raise ConanException("test.sh not found next to test_package/conanfile.py")

        self.run('bash "{}" "{}"'.format(script, jomon), env="conanrun")
