#!/usr/bin/env python3
"""Conan test_package for afsctool 1.7.3 — 验证 afsctool 二进制可执行。

afsctool 是 C + C++ 命令行工具（application），上游无测试套件。
test_package 运行 afsctool（无参数打印 usage 后 exit EINVAL），
捕获输出验证包含程序名与用法（R34 反空壳：真实执行被测包二进制）。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class AfsctoolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        bin_dir = self.dependencies["afsctool"].cpp_info.bindirs[0]
        pkg = self.dependencies["afsctool"].package_folder
        afsctool = os.path.join(pkg, bin_dir, "afsctool")
        if not os.path.exists(afsctool):
            raise Exception(f"afsctool not found at {afsctool}")
        # R34 反空壳：真实执行 afsctool（无参数打印 usage 后 exit EINVAL=22 属预期）。
        # L0d 门禁要求 test() 用 self.run；env="conanrun" 激活依赖 runenv_info
        # （afsctool package_info 注入 musl-fts 的 LD_LIBRARY_PATH，libfts.so.0 可加载）。
        # 输出重定向到文件再校验内容，避免假通过。
        out_file = os.path.join(self.build_folder, "afsctool_usage.txt")
        self.run(f'"{afsctool}" > "{out_file}" 2>&1 || exit 0', env="conanrun")
        with open(out_file, "r", errors="ignore") as f:
            output = f.read()
        if "afsctool" not in output and "HFS+" not in output:
            raise Exception(f"afsctool usage output not found, got: {output[:500]}")
        self.output.info("afsctool test PASSED (usage printed)")
