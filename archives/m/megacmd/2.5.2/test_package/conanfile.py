#!/usr/bin/env python3
"""Conan test_package for megacmd 2.5.2 — 真实执行打包的 CLI 二进制（R34）。

MEGAcmd 是 CLI 应用（无库消费者接口）：被测 API 就是可执行文件本身。
脚本对 bin/ 内的 mega-cmd / mega-exec / mega-cmd-server 逐个真实执行
`--version`（带 timeout 兜底，防止 server 前台驻留），要求至少一个产出
可解析的版本输出。

⚠ 不要加 `cross_building()` 早退守卫（曾加过，导致 W3 L1e 反向验证失败）：
CI 的 L1e 会先 `mv` 走包内 bin/ 再单独跑 `conan test … -pr <host profile>`
（**不带 `-pr:b`**），此时 build profile 回落到自动探测（Linux/armv8），
而 host profile 是 `os=OHOS` ⇒ `cross_building()` 判真 ⇒ test() 直接 return ⇒
`conan test` 退出 0 ⇒ 被判 "test does not depend on package"（假测试）。
本流水线全程在鸿蒙 PC 本机原生构建，不存在真交叉，全仓 test_package 也都
没有该守卫（0/N 命中）。
"""
import os

from conan import ConanFile


class MegacmdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_megacmd.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 可能无法可靠执行 ELF/包装脚本；
        # 统一用 bash（tag/aa3d 等先例同款处理）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_megacmd.sh")
        self.run(f"{bash} {script}", env="conanrun")
