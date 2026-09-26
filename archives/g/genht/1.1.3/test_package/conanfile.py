#!/usr/bin/env python3
"""Conan test_package for genht 1.1.3 (L1 consumer test).

CI runs this automatically through `conan create`.  The test binary is built
with the same CMakeDeps/CMakeToolchain generators every downstream consumer
would use (find_package(genht) → genht::genht), so it validates the exported
package layout rather than the build tree.

File location: archives/g/genht/1.1.3/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GenhtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # Bind stdout/stderr to a file: inheriting the parent streams makes the
        # OHOS compiler driver fail silently (log shows "Error 1" with no
        # diagnostic line).
        log_path = os.path.join(self.build_folder, "build.log")
        with open(log_path, "w", encoding="utf-8") as log:
            cmake.build(stdout=log, stderr=log)
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as log:
                self.output.info(log.read()[-1500:])
        except OSError:
            pass

    def test(self):
        # Run the consumer binaries explicitly: CMake uses CMAKE_SKIP_RPATH on
        # OHOS, so a binary only finds libgenht.so inside the conanrun
        # environment.
        #   test_genht    — API 断言用例（单元级）
        #   test_consumer — 鸿蒙特有测试：完整端到端消费者用例
        #                   （构造输入 → 真实执行 → 产出报告 → 校验参考输出）
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_genht"), env="conanrun")
        self.run(os.path.join(bindir, "test_consumer"), env="conanrun")
