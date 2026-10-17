#!/usr/bin/env python3
"""Conan test_package — simka 1.5.3（application 形态的消费者测试）。

simka 产物只有可执行文件（没有可链接的库、没有导出头文件），所以 R34/L1e
要求的"实质依赖被测包"只能靠**真跑被测二进制**来满足：本脚本调用包内
`bin/simka` 对上游自带示例数据集做 k-mer 计数，并把产出的距离矩阵与
上游 `tests/truth/` 的期望值逐字节比对（期望值内嵌在下面）。

把包产物 bin/ 移走后本脚本必然失败（找不到可执行文件），满足 L1e 破坏性反向验证。
"""
import os

from conan import ConanFile


class SimkaTestConan(ConanFile):
    """Runs test_simka.sh, which drives the packaged simka binaries."""

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["simka"].package_folder
        # OHOS 的 /system/bin/sh (mksh) 不能执行 ELF，必须用 bash 包装被测程序；
        # CONFIG_SHELL 由 ci/conan/profiles/ohos-aarch64 的 buildenv 提供。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test_simka.sh \"{pkg}\"", env="conanrun")
