#!/usr/bin/env python3
"""Conan recipe for darts-clone 0.32h (s-yata/darts-clone).

Darts-clone 是双数组 trie（Double-Array Trie）的 header-only C++ 实现：
静态词典压缩存储 + exactMatchSearch/commonPrefixSearch 检索，单头
include/darts.h，零第三方依赖（W0 预检通过）。

OHOS 适配要点：
- header-only：package() 只装 include/darts.h，package_id clear。
- 上游构建系统是 autotools（configure.ac/Makefile.am），但库本体无需编译；
  测试不依赖 autotools 生成物，build() 内直接编译实跑：
  (1) test/test-darts.cc：assert 自检（46 条断言，随机+固定键集构建/检索）；
  (2) test/test-tools.sh：编译 src/mkdarts.cc + src/darts.cc 两个 CLI 工具，
      mkdarts 建典 cmp correct-dic、darts 检索 cmp correct-result（字节级比对）。
- test-tools.sh 用相对路径 ../src/mkdarts，build() 内按上游目录语义在 test/
  副本里跑（工具二进制放进 src 副本）。
"""
from conan import ConanFile
from conan.tools.files import copy, get
import os


class DartsCloneConan(ConanFile):
    name = "darts-clone"
    version = "0.32h"
    description = "A header-only C++ implementation of a static double-array trie"
    license = "BSD-2-Clause"
    homepage = "https://github.com/s-yata/darts-clone"
    url = ""  # CI fills this
    topics = ("trie", "double-array", "dictionary", "search", "header-only")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _cxx(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get("cpp", "clang++") if compilers else "clang++"

    def build(self):
        src = self.source_folder
        cxx = self._cxx()
        inc = os.path.join(src, "include")
        # 层1 上游测试 1/2：test-darts（46 条 assert 自检）
        self.run(f"{cxx} -O2 -std=c++11 -I{inc} {os.path.join(src, 'test', 'test-darts.cc')} -o test-darts")
        self.run("./test-darts")
        # 层1 上游测试 2/2：test-tools.sh（mkdarts 建典 cmp correct-dic +
        # darts 检索 cmp correct-result）。脚本内用 ../src/{mkdarts,darts}，
        # 按上游目录语义摆副本再跑。
        self.run(f"{cxx} -O2 -std=c++11 -I{inc} -I{os.path.join(src, 'src')} {os.path.join(src, 'src', 'mkdarts.cc')} -o mkdarts")
        self.run(f"{cxx} -O2 -std=c++11 -I{inc} -I{os.path.join(src, 'src')} {os.path.join(src, 'src', 'darts.cc')} -o darts")
        tdir = os.path.join(self.build_folder, "tooltest")
        os.makedirs(os.path.join(tdir, "src"), exist_ok=True)
        os.makedirs(os.path.join(tdir, "test"), exist_ok=True)
        for f in ("mkdarts", "darts"):
            copy(self, f, src=self.build_folder, dst=os.path.join(tdir, "src"), keep_path=False)
        for f in ("test-tools.sh", "correct-dic", "correct-result", "test-lexicon", "test-text"):
            copy(self, f, src=os.path.join(src, "test"), dst=os.path.join(tdir, "test"), keep_path=False)
        self.run("sh test-tools.sh", cwd=os.path.join(tdir, "test"))

    def package(self):
        copy(self, "darts.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
