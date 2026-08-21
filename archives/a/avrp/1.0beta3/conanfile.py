#!/usr/bin/env python3
"""Conan recipe — avrp 1.0beta3 (AVR programmer — pure C, Makefile.linux build).

Build: make -f Makefile.linux (gcc——产出 avrp 二进制).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy


class AvrpConan(ConanFile):
    name = "avrp"
    version = "1.0beta3"
    description = "AVR programmer (programs AVR microcontrollers via serial)"
    license = "GPL-2.0-or-later"
    homepage = "https://savannah.nongnu.org/projects/avrp"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 C——Makefile.linux 构建——OHOS 无 gcc（实测 make: gcc: No such
        # file or directory——Error 127）——显式 CC=clang + LD=clang
        # （Makefile.linux 的 LD=gcc 需一并覆盖——链接阶段仍用 gcc）
        # lld 需 libxml2.so.16（在 OHOS SDK 的 llvm/lib——CI 实测链接崩溃
        # Error loading shared library libxml2.so.16）——LD_LIBRARY_PATH 前置
        llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        self.run(f"LD_LIBRARY_PATH={llvm_lib}:$LD_LIBRARY_PATH "
                 "make -f Makefile.linux CC=clang LD=clang", cwd=self.source_folder)

    def package(self):
        copy(self, "avrp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        for doc in ("avrp.def", "avrp.1", "COPYING", "README"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
