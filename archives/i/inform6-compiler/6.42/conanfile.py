#!/usr/bin/env python3
"""Conan recipe for inform6-compiler 6.42 — the Inform 6 interactive-fiction compiler.

Upstream is David Griffith's all-in-one Unix release `inform-6.42-r9`
(compiler 6.42 + Standard Library 6.12.7 + PunyInform 5.14.1, distributed via
the IF Archive; r9 is the final revision of the 6.42 release line). Only
`src/*.c` needs compiling (`make inform-6.42`); the library trees are plain
text data installed verbatim. The upstream `all` target also compiles the
demo/tutorial `.z5`/`.z3` files with the freshly cross-built binary —
impossible when cross-compiling — so those targets are skipped.

License: Artistic-2.0.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class Inform6CompilerConan(ConanFile):
    name = "inform6-compiler"
    version = "6.42"
    description = "Inform 6 compiler for Z-machine interactive fiction"
    license = "Artistic-2.0"
    homepage = "https://github.com/DavidKinder/Inform6"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # 上游 Makefile 按 uname 分支（Linux/Android/Darwin/其他），OHOS 属 POSIX 系。
    # R32: 显式 allow-list。
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"inform6-compiler supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        # R33: 编译器取自 Conan conf，绝不裸用 shell 环境变量。
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        return compilers.get("c", "clang") if compilers else "clang"

    def build(self):
        self._check_inventory()
        cc = self._cc()
        # 上游 Makefile 未给 CC 默认值（CC ?= gcc 被注释），必须显式传入。
        # 6.42 的编译器目标名是 $(BINNAME)=inform-6.42（无 inform 别名目标）；
        # 只编译 src/*.c 出编译器本体；stddemos/stdtutor/punyhowto/punytests
        # 目标需要用刚交叉编译出的二进制在构建机上运行，跳过。
        self.run(f"make CC={cc} inform-6.42", cwd=self.source_folder)

    def _check_inventory(self):
        """构建期防漂移校验（kicad-demos 先例范式）。"""
        src = self.source_folder
        for rel in ("src/inform.c", "src/header.h", "std/parser.h",
                    "std-include/dmenus.h", "std-demos/advent.inf",
                    "punyinform/lib/puny.h"):
            if not os.path.isfile(os.path.join(src, rel)):
                raise ConanInvalidConfiguration(
                    f"inform6-compiler 6.42 inventory drift: missing {rel}"
                )
        counts = {
            "std": 14, "std-include": 19, "std-demos": 9,
            "std-tutor": 11, "punyinform": 222,
        }
        for rel, expected in counts.items():
            actual = sum(len(fs) for _, _, fs in os.walk(os.path.join(src, rel)))
            if actual != expected:
                raise ConanInvalidConfiguration(
                    f"inform6-compiler 6.42 inventory drift: {rel} has {actual} "
                    f"files, expected {expected}"
                )

    def package(self):
        # 二进制：上游以版本名 inform-6.42 构建 + 软链 inform；此处以包名
        # inform6 直接落盘，规避软链（R5）。
        # 裸 copy2 不会自建目标目录（conan 的 copy() 会），需先建 bin/。
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(os.path.join(self.source_folder, "inform-6.42"),
                     os.path.join(bin_dir, "inform6"))
        datadir = os.path.join(self.package_folder, "share", "inform6")
        copy(self, "*", src=os.path.join(self.source_folder, "std"),
             dst=os.path.join(datadir, "std", "lib"))
        # 上游 fixlinks.sh 的 5 个大小写别名软链 → 文件副本（R5: 禁止 ln -sf）。
        for alias, real in (("English.h", "english.h"), ("Grammar.h", "grammar.h"),
                            ("Parser.h", "parser.h"), ("Verblib.h", "verblib.h"),
                            ("VerbLib.h", "verblib.h")):
            try:
                shutil.copy2(os.path.join(datadir, "std", "lib", real),
                             os.path.join(datadir, "std", "lib", alias))
            except shutil.SameFileError:
                # 大小写不敏感文件系统（OHOS 真机 /storage）：别名与原名同
                # 文件，无需副本；大小写敏感系统（CI Linux）仍正常拷贝。
                pass
        copy(self, "*", src=os.path.join(self.source_folder, "std-include"),
             dst=os.path.join(datadir, "std", "include"))
        copy(self, "*", src=os.path.join(self.source_folder, "std-demos"),
             dst=os.path.join(datadir, "std", "demos"))
        copy(self, "*", src=os.path.join(self.source_folder, "std-tutor"),
             dst=os.path.join(datadir, "std", "tutor"))
        copy(self, "*", src=os.path.join(self.source_folder, "punyinform"),
             dst=os.path.join(datadir, "punyinform"))
        for f in ("README.md", "NEWS", "VERSION", "inform.1"):
            copy(self, f, src=self.source_folder,
                 dst=os.path.join(datadir, "docs"))
        copy(self, "*", src=os.path.join(self.source_folder, "docs"),
             dst=os.path.join(datadir, "docs", "src"))
        for lic in ("ARTISTIC", "COPYING"):
            copy(self, lic, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share/inform6"]
