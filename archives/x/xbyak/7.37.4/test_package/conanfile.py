#!/usr/bin/env python3
"""Conan test_package — xbyak 7.37.4 (header-only, manual compile)."""
import os
import shutil
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        cxx = os.environ.get("CXX", "clang++")
        cxxflags = os.environ.get("CXXFLAGS", "-std=c++11")
        # Conan 2.x build() 从 build_folder 执行，test.cpp 在 source_folder，
        # 必须用绝对路径避免 "file not found" 编译失败。
        test_src = os.path.join(self.source_folder, "test.cpp")
        self.run(f"{cxx} {cxxflags} {test_src} -o test_probe {inc}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译（x86/x64 JIT 在 aarch64 上不可运行）")
            return
        # 依次尝试 CONFIG_SHELL 环境变量、PATH 中的 bash、常见 OHOS 路径，
        # 避免硬编码单一路径在部分 worker 上不存在导致测试失败。
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        self.run(f"{bash} -c './test_probe'", env="conanrun")
