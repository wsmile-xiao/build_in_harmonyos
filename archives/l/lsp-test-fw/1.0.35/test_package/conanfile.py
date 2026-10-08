#!/usr/bin/env python3
"""Conan test_package — lsp-test-fw 消费者测试（L1）.

OHOS ELF 执行前置条件（harmonyos-recovery 知识库 03-permission-denied）：
可执行文件必须持有有效代码签名方可 exec。构建产物由 conan 编译器生成后
无签名，test() 内先自签名再执行，与 mesa 等 recipe 的 package() 签名步骤
同源（binary-sign-tool 位于 OpenHarmony 开发环境 /data/service/hnp/bin）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LspTestFwTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _sign_if_needed(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.exists(signer):
            return
        # strip a possibly stale signature section; missing is fine
        self.run(f'llvm-objcopy --remove-section=.codesign "{path}" "{path}"',
                 ignore_errors=True)
        self.run(f'"{signer}" sign -selfSign 1 -inFile "{path}" -outFile "{path}"')

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_lsp-test-fw")
        # OHOS 要求 ELF 持有有效签名才能 exec（无签名时 exec 返回 EPERM）
        self._sign_if_needed(exe)
        self.run(f'"{exe}"', env="conanrun")
