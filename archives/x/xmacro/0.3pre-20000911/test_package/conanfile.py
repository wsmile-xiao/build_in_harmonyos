#!/usr/bin/env python3
"""Conan test_package — xmacro 0.3pre-20000911 消费者冒烟测试

验证安装后的包可用 (R34): 通过 conanrun 环境实际执行被测包 bin/ 下三个
二进制:
1. xmacroplay -v  → stderr 打印 "xmacroplay 0.3", exit 0 (无需 X server);
2. xmacroplay     → 无参数, stderr 含 "Usage:", exit 非 0 (参数校验路径);
3. xmacrorec/xmacrorec2 二进制存在且可执行 (录制工具需 X 授权与键鼠
   事件, 无 X 环境下无法安全运行, 按平台限制降级为存在性检查)。

XTest 事件注入/录制路径需要真实 X server, 归入真机验证阶段, 此处不伪造。
"""
import os
import sys

from conan import ConanFile


class XmacroTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_bin = os.path.join(
            self.dependencies["xmacro"].package_folder, "bin")
        play = os.path.join(pkg_bin, "xmacroplay")

        # L0d 要求 self.run() 实际执行被测包二进制（非桩）:
        # xmacroplay -v 打印版本并 exit 0, 不需要 X server
        self.run('"%s" -v' % play, env="conanrun")

        # 完整 5 断言套件 (见 test_xmacro.py): 三二进制齐全 + -v 输出
        # + 无参 Usage 降级路径
        self.run(
            '"%s" "%s" "%s"' % (
                sys.executable,
                os.path.join(self.source_folder, "test_xmacro.py"),
                pkg_bin,
            ),
            env="conanrun",
        )
        self.output.info("xmacro test_package: 5/5 assertions passed")
