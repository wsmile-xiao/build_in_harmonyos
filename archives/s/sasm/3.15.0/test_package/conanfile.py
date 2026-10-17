#!/usr/bin/env python3
"""Conan test_package for sasm 3.15.0 — executes the packaged `sasm` GUI
binary headless (QT_QPA_PLATFORM=offscreen) and verifies it starts and stays
alive: this exercises ELF loadability, Qt5 plugin/translations/resource
loading and the singleapplication Network path (R34: real execution of the
tested package's binary, not a print-only stub)."""

import os

from conan import ConanFile


class SasmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindirs = self.dependencies["sasm"].cpp_info.bindirs
        if not bindirs:
            raise RuntimeError("sasm bindir was not produced")
        executable = os.path.join(bindirs[0], "sasm")
        if not os.path.isfile(executable):
            raise RuntimeError("sasm executable not found: " + executable)

        # 测试脚本以消费者视角实际执行 sasm 二进制（R34）：
        # offscreen 平台启动，8s 存活 = ELF/Qt5 插件/资源/Network 全链路加载成功。
        self.run('SASM_BIN="%s" bash test_sasm.sh' % executable, env="conanrun")
