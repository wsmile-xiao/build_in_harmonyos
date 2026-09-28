#!/usr/bin/env python3
"""Conan test_package for case.c 0.2.0.

消费者验证（R34/PF3 硬闸）：test.c 只通过 case.c 安装后的公开头文件
(case.h) 与公开 API (case_lower/case_upper/case_camel) 编译、链接并
实际运行，带三组断言，禁止空壳。
"""
import os

from conan import ConanFile


class CaseCTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # R33: 编译器从 Conan conf 获取
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # 消费者仅链接库公开产物（include + lib）
        self.run(f"{cc} -std=c99 test.c -I{self.dependencies['case.c'].cpp_info.includedirs[0]} "
                 f"-L{self.dependencies['case.c'].cpp_info.libdirs[0]} -lcase -o test_consumer")

    def test(self):
        # OHOS: mksh 不能执行 ELF，用 bash 包装
        bash = os.environ.get("CONFIG_SHELL") or next(
            (p for p in (
                "/data/service/hnp/bin/bash",
                "/bin/bash",
                "/usr/bin/bash",
            ) if os.path.exists(p)),
            "bash",
        )
        self.run(f"{bash} -c './test_consumer'", env="conanrun")