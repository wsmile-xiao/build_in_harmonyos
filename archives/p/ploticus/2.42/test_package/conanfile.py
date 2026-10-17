#!/usr/bin/env python3
"""Conan test_package — ploticus 2.42 (L1 消费者测试).

ploticus 交付面为可执行文件（``bin/pl``）+ 静态嵌入库（``lib/libploticus.a``），
因此 L1 测试通过**实际运行被测二进制**来验证（R34），测试逻辑在 ``test.sh``。

用例构成（见 test.sh / MANIFEST.yml）：
  1. version_banner          —— `pl -version` 报告版本与可用输出设备
  2. png_render              —— 渲染 PNG 并校验 PNG 魔数/IHDR 尺寸
  3. svg_render              —— 渲染 SVG 并校验矢量内容
  4. libploticus_api         —— 用打包的 libploticus.a + 头文件编译并运行 API 程序
  5. ohos_tmpdir_readonly    —— 【鸿蒙特有】TMPDIR 指向只读目录（/tmp）时，
                                proc drawcommands 仍能渲染成功（适配补丁）
  6. ohos_elf_abi            —— 【鸿蒙特有】bin/pl 为 aarch64 OHOS ELF，
                                且 zlib 静态链接（无 libz.so 运行时依赖）
  7. ohos_prefab_render      —— 【鸿蒙特有】用包内 prefabs（PLOTICUS_PREFABS 由
                                recipe 的 runenv 提供）渲染 prefab 出图
"""
import os

from conan import ConanFile


class PloticusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # 测试产物统一落在 build/（已在仓库 .gitignore 中），避免污染归档目录
        self.folders.build = "build"
        self.folders.generators = "build"

    def test(self):
        # HarmonyOS: /system/bin/sh (mksh) cannot execute ELF binaries, use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        pl_bin = os.path.join(self.dependencies["ploticus"].package_folder, "bin", "pl")
        pkg = self.dependencies["ploticus"].package_folder
        work = os.path.join(self.build_folder, "l1_out")
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict) or {}
        cc = compilers.get("c", "")
        self.run(
            f'{bash} "{os.path.join(self.source_folder, "test.sh")}" '
            f'"{pl_bin}" "{pkg}" "{work}" "{cc}"',
            env="conanrun",
        )
