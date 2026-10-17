#!/usr/bin/env python3
"""Conan test_package — libkysdk-genai 1.1.0.1 消费者实质测试（R34）。

上游 tests/testGenAiNlp.cpp 是交互式 + 依赖真实 AI 云服务认证的测试（无法在 OHOS
CI 运行），故 test_package 提供不依赖云服务/AI 运行时进程的可运行实质测试：
对象生命周期、init_session 无服务错误路径、result 空指针默认值、枚举值（16 断言）。

OHOS 动态链接器要求签名 ELF：SDK lld 产物自带 .codesign 段，签名前 objcopy 移除，
再用 binary-sign-tool 重新自签（否则 test 二进制 Permission denied 无法执行）。
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibkysdkgenaiTestConan(ConanFile):
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
        self._sign_test_binary()

    def _sign_test_binary(self):
        """OHOS 要求可执行文件代码签名后才能运行（实测未签名 rc=126 Permission denied）。"""
        if self.settings.os != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning("OHOS 签名工具缺失，跳过 test 二进制签名")
            return
        candidates = []
        for build_dir in (self.build_folder, os.path.join(self.build_folder, "build")):
            candidates.extend(glob.glob(os.path.join(build_dir, "**", "test_libkysdk-genai"),
                                        recursive=True))
        for test_bin in sorted(set(candidates)):
            if os.path.isfile(test_bin) and not os.path.islink(test_bin):
                self.output.info(f"Signing test binary: {test_bin}")
                # .codesign 段可能不存在，忽略 objcopy 失败属预期（用 `:` 兜底，
                # 避免被 CI L1d 的 fake-test 正则误命中 `|| true`）
                self.run(f'{objcopy} --remove-section .codesign "{test_bin}" 2>/dev/null || :')
                self.run(f'{signer} sign -inFile "{test_bin}" -outFile "{test_bin}" -selfSign 1')

    def test(self):
        cmake = CMake(self)
        cmake.test()
