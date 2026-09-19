#!/usr/bin/env python3
"""Conan test_package for criticalmass 1.0.2 (application).

critter 是 SDL 1.2/OpenGL 图形游戏，无显示/输入环境无法启动完整游戏主循环；
patches/0004 让 main() 在 SDL/GL 初始化之前处理 --version（stdout 输出
"Critical_Mass 1.0.2" 后 exit(0)），因此用 --version 做二进制真实性验证：

  - 正例：critter --version → stdout 含 "Critical_Mass 1.0.2" 且退出码为 0。

具体断言逻辑在 test.sh（L0c 门禁要求 test_package 下有测试源文件）。
上游无任何测试套件（无 test/ 目录、无 AC_CONFIG_TESTDIR/TESTS），
故版本级验证由此消费者冒烟承担（MANIFEST.yml 记录 upstream_tests: 0）。
"""
import os

from conan import ConanFile


class CriticalMassTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os not in ("Linux", "OHOS"):
            return

        pkg = self.dependencies["criticalmass"].package_folder
        critter = os.path.join(pkg, "bin", "critter")
        assert os.path.isfile(critter), f"critter not found at {critter}"

        # 调用测试脚本执行 critter --version 断言。
        # 输出用临时目录，避免把 version.out 写入 repo 的 test_package/（
        # conan create 时 build_folder==source_folder，直接写会污染工作树）
        import tempfile
        test_script = os.path.join(self.source_folder, "test.sh")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        with tempfile.TemporaryDirectory() as out_dir:
            self.run(f'{bash} "{test_script}" "{critter}" "{out_dir}"', env="conanrun")
