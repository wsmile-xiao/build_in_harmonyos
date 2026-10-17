#!/usr/bin/env python3
"""Conan test_package for incus-feature-agent — 消费者视角验证安装产物。

L1 测试：验证安装后的 incus-agent 可执行文件可用。
包含 1 个 OHOS 平台特有断言（binary 必须为已签名的 aarch64 ELF）。
"""
import os
import struct
import tempfile

from conan import ConanFile


class IncusFeatureAgentTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["incus-feature-agent"]
        binary = os.path.join(dep.package_folder, "bin", "incus-agent")
        self.output.info(f"testing installed binary: {binary}")
        assert os.path.isfile(binary), f"incus-agent binary missing: {binary}"

        # 用例 1（真实执行被测二进制）：--version 输出版本号
        # 上游 internal/version 声明为 "7.2"。输出写入临时目录，避免污染源码目录。
        with tempfile.TemporaryDirectory() as td:
            ver_file = os.path.join(td, "incus-agent-version.txt")
            self.run(f'"{binary}" --version > "{ver_file}"')
            with open(ver_file, encoding="utf-8") as fh:
                out = fh.read().strip()
        self.output.info(f"incus-agent --version -> {out!r}")
        assert out == "7.2", f"unexpected version output: {out!r}"

        # 用例 2：--help 正常返回（真实执行）
        self.run(f'"{binary}" --help')

        # 用例 3（鸿蒙特有）：产物必须是 aarch64 ELF 且带 OHOS .codesign 段
        # OHOS 内核拒绝加载未签名 ELF；此断言锁定平台适配结果（E318/E523）。
        with open(binary, "rb") as fh:
            data = fh.read()
        assert data[:4] == b"\x7fELF", "installed binary is not an ELF"
        e_machine = struct.unpack_from("<H", data, 18)[0]
        assert e_machine == 0xB7, f"expected AArch64 (0xB7), got {hex(e_machine)}"
        assert b".codesign" in data, "OHOS signature (.codesign) missing"
        self.output.info("OHOS-specific check OK: signed aarch64 ELF")
