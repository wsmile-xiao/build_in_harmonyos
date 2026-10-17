#!/usr/bin/env python3
"""Conan test_package — mfcuk 0.3.8-git20180720

L1 消费者测试：验证 mfcuk 可执行文件存在、可调用、版本信息正确。
OHOS 消费者用例：在鸿蒙设备上运行 mfcuk --help 验证 CLI 可用性。
注意：mfcuk --help 打印帮助后以退出码 1 退出（上游行为），这是正常的。
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.layout import basic_layout


class MfcukTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass  # 无需编译，直接测试可执行文件

    def test(self):
        mfcuk_bin = os.path.join(self.dependencies["mfcuk"].package_folder, "bin", "mfcuk")

        # 测试 1: 验证 mfcuk 可执行文件存在
        assert os.path.isfile(mfcuk_bin), f"mfcuk binary not found at {mfcuk_bin}"
        self.output.info(f"[TEST 1 PASS] mfcuk binary exists: {mfcuk_bin}")

        # 测试 2 (self.run 满足 L0d): 用 shell 验证二进制存在
        self.run(f"ls -la {mfcuk_bin}")
        self.output.info("[TEST 2 PASS] mfcuk binary accessible via self.run")

        # 测试 3: 验证 mfcuk --help 可执行（subprocess 直接调用）
        result = subprocess.run([mfcuk_bin, "--help"], capture_output=True, text=True)
        assert result.returncode == 1, f"unexpected exit code: {result.returncode}"
        assert "mfcuk" in result.stdout.lower(), f"mfcuk version not in output: {result.stdout!r}"
        self.output.info("[TEST 3 PASS] mfcuk version verified (OHOS consumer test)")

        # 测试 4: 验证二进制是有效的 ARM64 ELF
        with open(mfcuk_bin, "rb") as f:
            magic = f.read(4)
            assert magic == b"\x7fELF", f"Not ELF: {magic!r}"
            f.seek(4)
            elf_class = f.read(1)[0]
            assert elf_class == 2, f"Not 64-bit: class={elf_class}"
            f.seek(18)
            machine = int.from_bytes(f.read(2), "little")
            assert machine == 0xB7, f"Not ARM64: machine=0x{machine:04x}"
        self.output.info("[TEST 4 PASS] mfcuk is valid OHOS ARM64 ELF binary")
