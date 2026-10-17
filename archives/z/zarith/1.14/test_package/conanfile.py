#!/usr/bin/env python3
"""Conan test_package -- ZArith 1.14

Verifies that zarith library is installed and can perform big integer arithmetic.
Test: 42 + 1 = 43 (big integer addition).
"""
import os

from conan import ConanFile


class ZarithTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # 测试需要 ocaml 工具链（ocamlrun/ocamlc），声明为 tool_requires
        self.tool_requires("ocaml/4.14.1.1.4")

    def build(self):
        pass

    def test(self):
        # 通过 conan 依赖 API 获取 zarith 包路径，显式传给测试脚本
        zarith_pkg = self.dependencies["zarith"].package_folder
        # ocaml 是 tool_requires（build 依赖）：其配方可能未声明 bindirs，
        # conanbuild 环境不会自动注入 bin——显式注入 ocaml bin 到 PATH
        # （测试脚本需在 PATH 中找到 ocamlrun/ocamlc）
        ocaml_dep = self.dependencies.build["ocaml"]
        ocaml_bin = os.path.join(ocaml_dep.package_folder, "bin")
        os.environ["PATH"] = ocaml_bin + os.pathsep + os.environ.get("PATH", "")
        self.output.info(f"ocaml bin 注入 PATH: {ocaml_bin}")
        # 使用 conanbuild 环境使 ocaml 工具链（tool_requires bin）进入 PATH
        self.run(f"sh test_zarith.sh {zarith_pkg}", env="conanbuild", cwd=self.build_folder)
