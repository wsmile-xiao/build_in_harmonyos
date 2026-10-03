#!/usr/bin/env python3
"""test_package for velvet — 对安装产物执行上游测试套件 + 鸿蒙特有 e2e。

test.sh 内容（运行于 conanrun 环境，PATH 提供 bin/velveth、bin/velvetg）：
  U1-U5  上游官方测试套件 tests/run-tests.sh 的 5 个 .t 用例，脚本与数据
         原样来自上游（test_package/corpus/tests/），未做任何修改；
         上游脚本按 ../velveth 相对路径取二进制，本测试在临时工作目录按
         相同布局放置 shell 包装脚本（exec 已安装的真实 ELF，不复制/重命名
         ELF 本身，符合 OHOS codesign 约束）。
  H1     鸿蒙特有 e2e：安装产物 velveth → velvetg 完整组装流程在
         HarmonyOS 上真实执行，校验 Sequences/Roadmaps 与非空 contigs.fa
         （rule12：真实安装产物 → 实际调用 → 验证功能结果）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class VelvetTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            # macOS 开发机交叉编译：OHOS 二进制无法在本机执行，
            # 真实运行由 OHOS CI worker 完成。
            self.output.info(
                "skip run: cross-built OHOS binaries cannot execute on "
                "the build host (run is exercised on the OHOS CI worker)")
            return
        # OHOS: /system/bin/sh (mksh) 不能执行 ELF 二进制，用 bash 包裹执行。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{bash}" "{test_sh}"', env="conanrun")
