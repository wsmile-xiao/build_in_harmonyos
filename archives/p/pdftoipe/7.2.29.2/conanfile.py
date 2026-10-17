#!/usr/bin/env python3
"""Conan recipe — pdftoipe 7.2.29.2 (ipe-tools, Makefile-based terminal tool).

pdftoipe 把任意 PDF 转换成 Ipe 绘图编辑器可读的 XML；源码在 ipe-tools 单仓的
pdftoipe/ 子目录（无独立仓库）。

适配要点（源码零补丁）：
  * 上游 Makefile 用 `pkg-config --cflags/--libs poppler` 且默认 CXX=g++；
    OHOS 宿主无 g++、也无 pkg-config 的 poppler.pc，故配方在 make 命令行
    显式传入 CXX / CPPFLAGS / CXXFLAGS / LDFLAGS / LIBS（命令行变量优先于
    Makefile 内的 `+=`，因此 pkg-config 分支不会被求值，构建完全确定）。
  * pdftoipe 消费的是 poppler 的 **C++ 私有头**（Object.h / OutputDev.h /
    GfxState.h / goo/GooString.h …），物理位于 <poppler>/include/poppler
    （poppler.pc 的 Cflags 亦为该目录）。
  * 上游要求 poppler >= 0.86；本配方对齐制品仓 poppler/25.12.0
    （FONT_CONFIGURATION=generic，依赖仅 freetype + zlib）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class PdftoipeConan(ConanFile):
    name = "pdftoipe"
    version = "7.2.29.2"
    description = "pdftoipe converts PDF files into editable Ipe XML documents"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/otfried/ipe-tools"
    url = "https://github.com/otfried/ipe-tools"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("poppler/25.12.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"])

    def build(self):
        # R33: 编译器从 conan conf 取（tools.build:compiler_executables 是 dict），
        # 不依赖 shell 里的 CC/CXX
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++")

        poppler = self.dependencies["poppler"]
        freetype = self.dependencies["freetype"]

        # 私有头在 <include>/poppler；poppler.pc 的 Cflags 也是 -I<include>/poppler。
        # 有些 poppler 配方会把该子目录额外列进 includedirs，故统一按目录探测展开。
        inc_flags = []
        for inc_dir in poppler.cpp_info.includedirs:
            inc_flags.append("-I" + inc_dir)
            private_inc = os.path.join(inc_dir, "poppler")
            if os.path.isdir(private_inc):
                inc_flags.append("-I" + private_inc)
        if len(inc_flags) < 2:
            raise ConanInvalidConfiguration(
                "poppler 包未提供 C++ 私有头（include/poppler），pdftoipe 无法编译")
        for inc_dir in freetype.cpp_info.includedirs:
            inc_flags.append("-I" + inc_dir)

        # freetype 是 libpoppler.so 的 DT_NEEDED，链接期需可搜索到（运行期由 conanrun 提供）。
        lib_flags = []
        for lib_dir in list(poppler.cpp_info.libdirs) + list(freetype.cpp_info.libdirs):
            lib_flags.append("-L" + lib_dir)
        lib_flags.append("-lpoppler")

        make_vars = " ".join([
            "CXX='{}'".format(cxx),
            "CPPFLAGS='{}'".format(" ".join(inc_flags)),
            "CXXFLAGS='-O2 -fPIC -std=c++20 -Wno-write-strings'",
            "LDFLAGS=''",
            "LIBS='{}'".format(" ".join(lib_flags)),
        ])
        # R9: 固定 -j1；源码零补丁，故无需 apply_conandata_patches
        self.run("make -j1 " + make_vars, cwd=os.path.join(self.source_folder, "pdftoipe"),
                 env="conanbuild")

    def package(self):
        copy(self, "gpl.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        src = os.path.join(self.source_folder, "pdftoipe")
        copy(self, "pdftoipe", src, os.path.join(self.package_folder, "bin"))
        copy(self, "pdftoipe.1", src, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
