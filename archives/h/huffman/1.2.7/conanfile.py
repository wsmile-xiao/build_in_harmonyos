#!/usr/bin/env python3
"""Conan recipe for huffman 1.2.7 (upstream Makefile build).

huffman 是一个纯 C 的 Huffman 编解码库 + huffcode 命令行工具。
上游使用裸 Makefile（无 configure、无 install target），产物为
libhuffman.a 与 huffcode；本配方按 library 打包 libhuffman.a + huffman.h。
"""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class HuffmanConan(ConanFile):
    name = "huffman"
    version = "1.2.7"
    description = "A huffman coding library and command line interface"
    license = "Unlicense"
    homepage = "https://github.com/drichardson/huffman"
    url = "https://github.com/drichardson/huffman"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    package_type = "library"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("huffman requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        # R33: 编译器从 Conan conf 获取，禁止裸用 shell 环境变量
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        # R9: 单 job；上游 Makefile 无 install target，由 package() 复制产物
        self.run("make -j1 CC={} AR={}".format(cc, ar))
        # 上游单元测试（run_tests.sh shebang 依赖 /bin/bash，OHOS 无此路径，
        # 显式用 bash 调用；依赖上方 make 产出的 ./huffcode）
        self.run("bash run_tests.sh")

    def package(self):
        # 与上游 CMakeLists INSTALL(FILES huffman.h DESTINATION include/huffman) 一致
        copy(self, "huffman.h", self.source_folder,
             os.path.join(self.package_folder, "include", "huffman"))
        copy(self, "libhuffman.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["huffman"]
        self.cpp_info.includedirs = ["include"]
