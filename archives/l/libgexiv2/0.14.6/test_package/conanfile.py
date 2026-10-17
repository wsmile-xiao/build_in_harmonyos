#!/usr/bin/env python3
"""Conan test_package — libgexiv2/0.14.6（Conan L1 官方测试）。

实质调用被测包 C API（R34），见 test.c：
  1. 编译期版本宏 vs 运行期 gexiv2_get_version()
  2. gexiv2_initialize() + GExiv2Metadata 打开真实 JPEG 并做标签读写往返
  3. 【鸿蒙特有用例】__OHOS__ 下 dlopen("libgexiv2.so.2") + dlsym 复核
     OHOS 加载器能解析运行时共享库（平台特有风险点）

OHOS 专有处理：
  * 构建出的测试二进制必须用 binary-sign-tool 签名，否则内核 exec 门禁
    直接抛 SIGTRAP（signal 5）—— 仓库内 1591 个配方同款做法。
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

SIGNER = "/data/service/hnp/bin/binary-sign-tool"


class Gexiv2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._sign_test_binary()

    def _test_binary(self):
        return os.path.join(self.cpp.build.bindirs[0], "test_gexiv2")

    def _sign_test_binary(self):
        """OHOS 内核 exec 门禁要求合法 .codesign，未签名二进制直接 SIGTRAP。"""
        if self.settings.os != "OHOS" or not os.path.isfile(SIGNER):
            return
        binary = self._test_binary()
        if not os.path.isfile(binary):
            return
        self.run(shlex.join([SIGNER, "sign", "-inFile", binary,
                             "-outFile", binary, "-selfSign", "1"]))
        self.output.info(f"test_package: signed {binary}")

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: consumer binary runs on OHOS device")
            return
        # OHOS 的 /system/bin/sh（mksh）不能 exec ELF，必须经 bash 执行。
        bash = (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        self.run(f'{bash} -c "./test_gexiv2"', env="conanrun")
