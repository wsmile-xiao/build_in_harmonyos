import os

from conan import ConanFile


class PcctsTestConan(ConanFile):
    """test_package — 验证 pccts 四个生成器工具真实可执行且能完成一次
    端到端的「语法 → 生成 → 编译 → 运行」闭环。"""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh 无法执行 ELF，须经 bash 包一层（模板同款口径）
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
