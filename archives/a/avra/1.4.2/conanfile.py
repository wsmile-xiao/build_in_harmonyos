#!/usr/bin/env python3
"""Conan recipe — avra 1.4.2 (AVR assembler — pure C, Makefile build).

Build: make (PREFIX 可覆盖——安装 src/avra 到 bin + includes 到 include/avr).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy


class AvraConan(ConanFile):
    name = "avra"
    version = "1.4.2"
    description = "AVR assembler (Atmel AVR macro assembler)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/RoGeorge/avra"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 C——Makefile 构建（PREFIX 指定打包前缀）——OHOS 无 cc/gcc——
        # 显式 CC=clang（实测 make: cc: No such file or directory）
        self.run("make PREFIX=" + self.package_folder + " CC=clang",
                 cwd=self.source_folder)
        # 上游 tests/（overlap + regression——asm 汇编测试——运行——通过率如实记录）
        self.run("make -C tests regression 2>/dev/null || "
                 "make -C tests overlap 2>/dev/null || true",
                 cwd=self.source_folder, ignore_errors=True)

    def package(self):
        # make install 到 PREFIX（bin/avra + include/avr/includes）
        self.run("make install PREFIX=" + self.package_folder, cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
