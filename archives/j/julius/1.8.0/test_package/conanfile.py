#!/usr/bin/env python3
"""Conan test_package for julius 1.8.0 (application).

julius 是 SDL2 图形游戏，无显示环境无法完整启动游戏主循环；但参数解析发生在
SDL 初始化之前（main() 内先 platform_parse_arguments，出错即 exit_with_status(1)，
不进入 setup()/SDL 初始化）。因此用 julius 的 CLI 参数入口做二进制真实性验证：

  - 正例：julius --help → stdout 含 "Usage: julius"（退出码为 1 属预期：
    Linux 分支 parse 失败即 exit(1)，用输出内容断言，不依赖退出码）；
  - 负例（E003）：julius --definitely-invalid-option → 必须被拒绝
    （输出含 "not recognized" 且退出码非 0）。

具体断言逻辑在 test.sh（L0c 门禁要求 test_package 下有测试源文件）。
"""
import os

from conan import ConanFile


class JuliusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os not in ("Linux", "OHOS"):
            return

        pkg = self.dependencies["julius"].package_folder
        julius = os.path.join(pkg, "bin", "julius")
        assert os.path.isfile(julius), f"julius not found at {julius}"

        # 调用测试脚本执行 julius --help 与非法参数负向断言。
        # 输出用临时目录，避免把 help.out/bad.out 等写入 repo 的 test_package/（
        # conan create 时 build_folder==source_folder，直接写会污染工作树）
        import tempfile
        test_script = os.path.join(self.source_folder, "test.sh")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        with tempfile.TemporaryDirectory() as out_dir:
            self.run(f'{bash} "{test_script}" "{julius}" "{out_dir}"', env="conanrun")
