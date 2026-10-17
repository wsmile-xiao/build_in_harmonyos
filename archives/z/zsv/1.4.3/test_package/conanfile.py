import os

from conan import ConanFile


class ZsvTestConan(ConanFile):
    """test_package for zsv — 执行 zsv 主二进制并断言输出（R34 实质使用被测包）。"""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv 仅对 run 依赖注入 bin 目录到 PATH，
        # zsv 为 CLI 工具（library 类型，默认 run=False），否则 test.sh 找不到 zsv 命令
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
