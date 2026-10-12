#!/usr/bin/env python3
"""Conan test_package for incus-user — 消费者视角验证安装产物。

L1 测试：验证安装后的 incus-user 可执行文件可用。
包含 1 个 OHOS 平台特有断言（binary 必须为已签名的 aarch64 ELF）。
"""
import os
import struct
import subprocess

from conan import ConanFile


class IncusUserTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["incus-user"]
        binary = os.path.join(dep.package_folder, "bin", "incus-user")
        self.output.info(f"testing installed binary: {binary}")

        # 用例 1/2：实际执行被测二进制（--version / --help 必须退出码 0）
        self.run(f'"{binary}" --version', env="conanrun")
        self.run(f'"{binary}" --help', env="conanrun")

        # 用例 3：--version 输出必须是 7.0.1
        out = subprocess.run([binary, "--version"], capture_output=True,
                             text=True, timeout=60).stdout.strip()
        self.output.info(f"incus-user --version -> {out!r}")
        assert out == "7.0.1", f"unexpected version output: {out!r}"

        # 用例 4（鸿蒙特有）：产物必须是 aarch64 ELF 且带 OHOS .codesign 段
        # OHOS 内核拒绝加载未签名 ELF；此断言锁定平台适配结果（E523/E318）。
        with open(binary, "rb") as fh:
            data = fh.read()
        assert data[:4] == b"\x7fELF", "installed binary is not an ELF"
        e_machine = struct.unpack_from("<H", data, 18)[0]
        assert e_machine == 0xB7, f"expected AArch64 (0xB7), got {hex(e_machine)}"
        assert b".codesign" in data, "OHOS signature (.codesign) missing"
        self.output.info("OHOS-specific check OK: signed aarch64 ELF")
