#!/usr/bin/env python3
"""lz4 test_package — 消费者用例：模拟上层组件调用 LZ4 公开 API.

消费者验证（业务上层视角）：
  1. 编译：引入 lz4.h 编译（-I include）
  2. 链接：-llz4 链接 liblz4.a
  3. 调用跑通：LZ4_compress_default / LZ4_decompress_safe /
     LZ4_versionNumber 实际压缩-解压往返并校验数据
*/
"""
import os
from conan import ConanFile
from conan.tools.build import can_run


class Lz4TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            import subprocess
            cc_map = self.conf.get("tools.build:compiler_executables",
                                   default={}) or {}
            cc = cc_map.get("c") or os.environ.get("CC", "clang")
            lz4 = self.dependencies["lz4"]

            src = os.path.join(self.source_folder, "src", "test_lz4.c")
            out = os.path.join(self.build_folder, "test_lz4")
            inc = os.path.join(lz4.package_folder, "include")
            lib = os.path.join(lz4.package_folder, "lib")

            self.run(
                f"{cc} -o {out} {src} -I{inc} -L{lib} -llz4",
                env="conanbuild")
            self.run(out, env="conanrun")
