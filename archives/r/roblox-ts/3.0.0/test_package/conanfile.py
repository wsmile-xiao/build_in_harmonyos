#!/usr/bin/env python3
"""Conan test_package — roblox-ts 3.0.0（消费者视角验证）

被测物为打包后的 Node.js CLI（bin/rbxtsc）；L1 smoke test 真实执行该启动器
（R34：不得空壳），并校验安装产物与上游 npm 发布包逐字节一致。

OHOS 相关：test.sh 内两条 [OHOS] 用例覆盖启动器的解释器解析与 shebang 加固，
另有一条 OHOS 内核识别用例（非 OHOS 主机 skip）。
"""
import os
import shutil

from conan import ConanFile


class RobloxTsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # 同主配方：OHOS settings.yml 为 OHOS 定义 version 子设置且无默认值，
        # 未声明 os.version 时 test_package 自身 package_id 校验会报
        # "Invalid: 'settings.os.version' value not defined"；rm_safe 移除之。
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["roblox-ts"].package_folder

        # 真实执行测试脚本（含 rbxtsc --version/--help/错误路径/完整性/sha256/OHOS 用例）。
        # 不套 conanrun env 文件、显式给出干净 PATH：Node.js 是与 C/C++ 无关的自包含
        # 运行时，继承 conan 的 C/C++ 环境（LD_LIBRARY_PATH 指向 SDK llvm/lib / PATH
        # 混入构建工具链）会让 node 异常终止（Native stack trace / SIGABRT）。
        shell = (shutil.which("bash") or shutil.which("sh")
                 or "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'PATH="/data/service/hnp/bin:/usr/bin:/bin" "{shell}" "{script}" "{pkg_folder}"',
                 env=None)

        # python 侧兜底存在性检查
        for rel in ("bin/rbxtsc",
                    "libexec/roblox-ts/out/CLI/cli.js",
                    "libexec/roblox-ts/out/CLI/index.js",
                    "libexec/roblox-ts/include/RuntimeLib.lua",
                    "libexec/roblox-ts/package.json",
                    "licenses/LICENSE"):
            p = os.path.join(pkg_folder, rel)
            if not os.path.isfile(p) or os.path.getsize(p) == 0:
                raise AssertionError(f"Missing/empty packaged file: {p}")
            self.output.info(f"  [ok] {rel}")
