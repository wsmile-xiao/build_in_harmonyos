#!/usr/bin/env python3
"""Test package for netris — R34: must exercise the netris binary.

netris is an interactive curses game, so we verify:
1. Binary exists and runs (netris -h exits 0)
2. Binary reports correct version string
3. sr sample robot binary is packaged
"""
import os

from conan import ConanFile


class NetrisTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: 实际执行 netris 二进制（经 test.sh 驱动，非空壳）
        netris_dep = self.dependencies["netris"]
        netris_bin = os.path.join(netris_dep.package_folder, "bin", "netris")
        sr_bin = os.path.join(netris_dep.package_folder, "bin", "sr")
        if not os.path.exists(netris_bin):
            raise Exception(f"netris binary not found at {netris_bin}")
        # 执行 test.sh：通过 shell 变量传递路径（Conan 2.x run() 不支持 vars 参数）
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(
            f'NETRIS_BIN="{netris_bin}" SR_BIN="{sr_bin}" bash "{test_script}"',
            env="conanrun",
        )
        self.output.info("netris binary executed successfully (test.sh: netris -h)")
