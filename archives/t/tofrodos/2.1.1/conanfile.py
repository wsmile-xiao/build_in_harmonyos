#!/usr/bin/env python3
"""Conan recipe — tofrodos 2.1.1（DOS/Unix 文本行结束符转换工具）

tofrodos 提供 fromdos/todos 两个命令（纯 C，Makefile 构建，
makefile.gcc，无 autotools），零第三方依赖（仅标准库）满足 R36。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class TofrodosConan(ConanFile):
    name = "tofrodos"
    version = "2.1.1"
    description = "tofrodos — convert text files between DOS/Windows and Unix line endings"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ChristopherHeng/tofrodos"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    # OHOS profile 要求四项 settings（L0p 门禁）；纯 C 需与 profile 对齐
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        # makefile.gcc：CC 覆盖为 clang；-j1（沙箱无 mkfifo jobserver）
        self.run(
            "make -f makefile.gcc CC=/data/service/hnp/bin/clang -j1",
            cwd=self.source_folder,
        )

    def package(self):
        src = self.source_folder
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        # 复制二进制；todos 用复制替代符号链接（HMDFS 拒绝 ln -s）
        copy(self, "fromdos", src=src, dst=bin_dst, keep_path=False)
        copy(self, "todos", src=src, dst=bin_dst, keep_path=False)
        # License
        copy(self, "COPYING-GPL2.txt", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
