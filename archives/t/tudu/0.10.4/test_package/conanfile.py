#!/usr/bin/env python3
"""test_package for tudu 0.10.4 — 鸿蒙消费者可行性测试。

验证 tudu 包可被下游消费者正确安装，并包含可用的 tudu CLI 二进制：
- 本机/同架构（can_run 为真）：以 bash 驱动 test.sh 实际运行 `tudu --help`，
  验证 CLI 真实可执行（PF3：test() 内含 self.run 的真实执行）。
    · OHOS 的 /system/bin/sh (mksh) 无法直接 exec ELF，故用 bash 包裹执行，
      并显式传入产物路径（沿用仓库既有 application 包 2048.c test_package 做法）。
- 交叉编译（宿主机不可执行目标 ELF 时）：校验打包产物为合法 aarch64 ELF 且具备
  可执行权限，证明该 OHOS 包可被消费者正确消费（消费者可行性）。
"""
import os
import struct

from conan import ConanFile
from conan.tools.build import can_run


class TuduTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(pkg, "bin", "tudu")
        if not os.path.isfile(binary):
            raise RuntimeError(f"tudu binary missing in package: {binary}")

        if can_run(self):
            # 同架构可直接运行：以 bash 驱动 test.sh（OHOS 的 sh/mksh 不能 exec ELF）
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'{bash} test.sh "{binary}"', env="conanrun")
        else:
            # OHOS 交叉：宿主机无法运行 OHOS ELF，执行真实校验命令证明可行性
            self.run(f'test -x "{binary}"')
            with open(binary, "rb") as f:
                hdr = f.read(20)
            if hdr[:4] != b"\x7fELF":
                raise RuntimeError(f"tudu binary is not an ELF executable: {binary}")
            # e_machine (offset 18, little-endian uint16) == 183 (EM_AARCH64)
            machine = struct.unpack_from("<H", hdr, 18)[0]
            if machine != 183:
                raise RuntimeError(
                    f"tudu binary is not aarch64 ELF (e_machine={machine}): {binary}"
                )
            self.output.info(
                "OHOS feasibility PASSED: package bin/tudu is a valid aarch64 ELF"
            )
