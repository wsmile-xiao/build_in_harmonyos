#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test.

Tests c-ares library initialization, version query, and cleanup.
File location: archives/c/c-ares/1.34.5/test_package/conanfile.py
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class CaresTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _llvm_lib_dir(self):
        """E266: OHOS SDK 的 lld 动态链接 libxml2.so.16，CI worker 沙箱默认库
        搜索路径找不到 → lld 无法启动 → CMake try_compile 链接失败（CI #30716，
        同主配方 #30626 / babeltrace #30527）。前置 SDK llvm/lib 到
        LD_LIBRARY_PATH（glob 兜底 SDK 版本目录），让 lld 加载到正确的 libxml2。
        与主配方 conanfile.py generate() 的 E266 修复一致。"""
        if str(self.settings.os) != "OHOS":
            return ""
        _llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if not os.path.isdir(_llvm_lib):
            _cands = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
            _llvm_lib = _cands[0] if _cands else ""
        return _llvm_lib

    def build(self):
        env = Environment()
        _llvm_lib = self._llvm_lib_dir()
        if _llvm_lib:
            env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
        cmake = CMake(self)
        with env.vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_c-ares'", env="conanrun")
