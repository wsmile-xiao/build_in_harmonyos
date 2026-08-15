#!/usr/bin/env python3
"""test_package for algotutor 0.8.6 — 消费测试。

algotutor 是纯 Perl 脚本程序（无编译），上游 12 个测试需 Tk GUI + X display，
headless 环境无法运行。消费测试验证：
1. bin/algotutor 及算法模块安装完整（dp/graph/cgeom/data 目录）
2. perl -c 语法检查不依赖 Tk 的算法模块（basic.pl/Graph.pm/BST.pm 等）
3. data/*.gr 数据文件存在
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class AlgotutorTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bin_dir = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "bin")
        # 1) 安装布局检查
        for f in ("algotutor", "utilalgo", "basic.pl"):
            p = os.path.join(bin_dir, f)
            if not os.path.exists(p):
                raise ConanException(f"missing installed file: {p}")
        for sub in ("dp", "graph", "cgeom", "data"):
            p = os.path.join(bin_dir, sub)
            if not os.path.isdir(p):
                raise ConanException(f"missing installed dir: {p}")
        # 2) perl -c 语法检查不依赖 Tk 的算法模块（-I bin_dir 供 use Vector2 等解析）
        for mod in ("basic.pl", "Graph.pm", "BST.pm", "Heap.pm", "Vector2.pm", "Configurable.pm"):
            p = os.path.join(bin_dir, mod)
            if not os.path.exists(p):
                raise ConanException(f"missing module: {p}")
            if self.run(f"perl -I {bin_dir} -c {p}") != 0:
                raise ConanException(f"perl -c failed: {p}")
        # 3) 数据文件存在
        for gr in ("countries.gr", "pts1.gr", "tt.gr"):
            p = os.path.join(bin_dir, "data", gr)
            if not os.path.exists(p):
                raise ConanException(f"missing data file: {p}")
