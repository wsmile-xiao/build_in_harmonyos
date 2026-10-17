#!/usr/bin/env python3
"""Conan test_package — netmask 2.5.0

R34：test_package 必须实质依赖被测包。netmask 是纯 CLI 工具（无库 API），因此采用
"执行被测包二进制 + 断言真实输出"的方式（与归档中 CLI 类包 b2sum/bash/whois
一致，均以 test.sh 驱动，无需 test.c——无可链接库）。

实质测试逻辑：test.sh **完整复刻上游 v2.5.0 testscript 的全部 34 个 check**（上游
make check 实测 34/34 ok）。每条用例真实执行 netmask 二进制，将 stdout 与本
test_package 携带的 fixtures/（上游 tests/ 34 个期望文件的逐字节拷贝）做
`diff -au`（与上游 `eval $3 | diff -au $2 -` 同语义），任一失败 exit 1，非
print-only 空壳。期望数据全部源自官方 release 资产 netmask-2.5.0.tar.gz
（sha256 实测一致），且本二进制输出已于 2026-09-04 W3 make check 逐字节核对通过。
"""
import os

from conan import ConanFile


class NetmaskTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: 平台判断必须 in ("Linux", "OHOS")，不能 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            return

        netmask_bin = os.path.join(
            self.dependencies["netmask"].package_folder, "bin", "netmask"
        )
        assert os.path.isfile(netmask_bin), f"netmask binary not found at {netmask_bin}"

        # OHOS 上沿用归档惯例（b2sum/bash test_package）：用 CONFIG_SHELL
        # （默认 /data/service/hnp/bin/bash）显式以 bash 执行 test.sh。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'NETMASK_BIN="{netmask_bin}" {bash} test.sh', env="conanrun")
