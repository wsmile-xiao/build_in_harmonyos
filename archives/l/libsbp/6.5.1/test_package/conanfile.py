#!/usr/bin/env python3
"""Conan test_package for libsbp/6.5.1 — consumer smoke test (pure C).

Exercises the public API of the packaged library: crc16_ccitt known
vector, heartbeat message encode/decode roundtrip and full frame
send/process roundtrip through sbp_message_send + sbp_process.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibsbpTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libsbp")
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        # 纯 C 静态库：运行时仅依赖 libc.so（/system/lib64 由 OHOS 系统提供）。
        # 沿用 scnlib 先例显式 LD_LIBRARY_PATH，保持与仓内其他包一致。
        self.run(
            f'{bash} -c "LD_LIBRARY_PATH=/system/lib64 {test_bin}"',
            env="conanrun",
        )
