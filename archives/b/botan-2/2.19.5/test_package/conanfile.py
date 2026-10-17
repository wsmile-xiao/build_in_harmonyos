#!/usr/bin/env python3
"""botan-2 test_package — 消费者用例：模拟上层组件调用 Botan 公开 API.

消费者验证（业务上层视角）：
  1. 编译：引入 botan/botan.h 编译（-I include/botan-2）
  2. 链接：-lbotan-2 链接 libbotan-2.a
  3. 调用跑通：Botan::AutoSeeded_RNG + SHA-256 哈希实际运行
"""
import os
from conan import ConanFile
from conan.tools.build import can_run


class Botan2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            cc_map = self.conf.get("tools.build:compiler_executables",
                                   default={}) or {}
            cc = cc_map.get("cpp") or cc_map.get("c") or os.environ.get(
                "CXX", "clang++")
            botan = self.dependencies["botan-2"]

            src = os.path.join(self.source_folder, "src", "test_botan.cpp")
            out = os.path.join(self.build_folder, "test_botan")
            inc = os.path.join(botan.package_folder, "include", "botan-2")
            lib = os.path.join(botan.package_folder, "lib")

            self.run(
                f"{cc} -o {out} {src} -I{inc} -L{lib} -lbotan-2 -lpthread -ldl -lm",
                env="conanbuild")
            self.run(out, env="conanrun")
