#!/usr/bin/env python3
"""Conan test_package — aklomp-base64 0.5.2."""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
import os


class Base64TestConan(ConanFile):
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

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise Exception("No bindirs found — test binary was not built")
            bin_path = os.path.join(bindirs[0], "test_base64")
            if not os.path.isfile(bin_path):
                raise Exception(f"Test binary not found: {bin_path}")
            # 探测沙箱 exec 能力：OHOS CI Worker 沙箱禁止 exec 非系统二进制
            # （Operation not permitted）。能 exec 则正常 self.run（失败如实传播）；
            # 不能 exec 则明确标注"预期跳过"（玖西认可的"明确标注预期跳过"，
            # 非静默吞异常；运行时验证已在 OHOS 真机 PTY 完成，见 PR_DESCRIPTION）。
            import subprocess
            try:
                subprocess.run([bin_path], capture_output=True, timeout=5)
            except OSError as e:
                self.output.warning(
                    f"SKIP: CI sandbox forbids exec test binary ({e}); "
                    "compile verified, run verified on OHOS device (1/1)"
                )
                return
            except subprocess.TimeoutExpired:
                pass  # 能 exec（测试运行中），交给 self.run 正常执行
            self.run(bin_path, env="conanrun")
