import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["checksecurity"].package_folder
        # L0c 门禁：独立测试源文件 + self.run 执行（backup2l test_backup2l.py
        # 模式）。checksecurity 主脚本需 root 才能完整运行（非 root 直接
        # 输出 "only root can run" 退出 1），故独立脚本用 perl -c 对主脚本
        # 与 perl 插件做真实语法校验（os.path 内核对 OHOS perl 可解析），
        # 并逐项核对 5 个 shell/perl 插件与配置文件装齐。
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_checksecurity.py")
        self.run(f"python3 '{test_script}' '{pkg}'", env="conanrun")