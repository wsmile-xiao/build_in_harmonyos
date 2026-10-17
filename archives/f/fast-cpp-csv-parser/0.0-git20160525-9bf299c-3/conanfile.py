#!/usr/bin/env python3
"""Conan recipe for fast-cpp-csv-parser 0.0-git20160525-9bf299c-3 — header-only C++ CSV parser.

fast-cpp-csv-parser is a header-only C++11 CSV parser (single header
csv.h). No build system — package installs the header. Upstream has no
formal test suite (only .clusterfuzzlite fuzz harness) — rule 4 honest
record; R34 consumer verification compiles+runs a real parse.
"""
import os

from conan import ConanFile
from conan.tools.files import get


class FastCppCsvParserConan(ConanFile):
    name = "fast-cpp-csv-parser"
    version = "0.0-git20160525-9bf299c-3"
    description = "fast-cpp-csv-parser — header-only C++11 CSV parser"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ben-strasser/fast-cpp-csv-parser"
    url = ""

    # header-only，无编译产物——但 OHOS profile 要求 settings 含全部四项
    # （CI L0p 门禁实测：缺 compiler/build_type 构建失败）
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only——无编译；无正式测试套件（仅 .clusterfuzzlite 模糊
        # 测试）——rule 4 如实记录，R34 消费验证代替
        pass

    def package(self):
        # header-only：安装 csv.h（单头文件）
        import shutil
        inc_dir = os.path.join(self.package_folder, "include")
        os.makedirs(inc_dir, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "csv.h"),
                    os.path.join(inc_dir, "csv.h"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
