#!/usr/bin/env python3
"""Conan test_package — asmjit 0.0-git20231115.1da9e4d

L1 官方测试：编译并运行 test.cpp，验证 asmjit JIT 核心流程。
"""
import os
import glob

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AsmjitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
            sysroot = os.environ.get("ASMJIT_SYSROOT", "")
            if not sysroot:
                home = os.environ.get("HOME", "/storage/Users/currentUser")
                sysroot = os.path.join(home, "usr", "local", "sysroot")
            if os.path.isdir(sysroot):
                tc.variables["CMAKE_SYSROOT"] = sysroot
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _sign_test_binary(self):
        """OHOS 要求可执行文件代码签名后才能运行"""
        if self.settings.os != "OHOS":
            return
        home = os.environ.get("HOME", "/storage/Users/currentUser")
        objcopy = os.path.join(home, "usr", "local", "bin", "llvm-objcopy")
        signer = os.path.join(home, "usr", "local", "bin", "binary-sign-tool")
        if not os.path.isfile(objcopy):
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            signer = "/data/service/hnp/bin/binary-sign-tool"
        # 签名 build 目录中的 test 二进制
        build_dir = os.path.join(self.source_folder, "build")
        for test_bin in glob.glob(os.path.join(build_dir, "**", "test_asmjit"), recursive=True):
            if os.path.isfile(test_bin) and not os.path.islink(test_bin):
                self.output.info(f"Signing test binary: {test_bin}")
                self.run(f'{objcopy} --remove-section .codesign "{test_bin}" 2>/dev/null || true')
                self.run(f'{signer} sign -inFile "{test_bin}" -outFile "{test_bin}" -selfSign 1')

    def test(self):
        self._sign_test_binary()
        cmake = CMake(self)
        cmake.test()
