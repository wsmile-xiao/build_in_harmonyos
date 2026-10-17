#!/usr/bin/env python3
"""Consumer test for GNU zile 2.6.4 (tool package).

zile ships no linkable public API — the zile binary is the product, so the
consumer test executes the packaged binary and asserts observable behaviour
through test_zile.sh (version banner, usage output and a batch lisp edit
round trip mirroring the upstream tests/*.el mechanism).
"""
import os

from conan import ConanFile


class ZileTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # zile 为 curses 程序：批处理执行 lisp 需要 terminfo 数据库，
        # 设备无系统 terminfo，由 ncurses 包（zile 的传递依赖）提供。
        self.requires("ncurses/6.5")

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        script = os.path.join(self.source_folder, "test_zile.sh")
        # ncurses 包根（含 share/terminfo），供批处理断言设置 TERMINFO
        term_root = self.dependencies["ncurses"].package_folder
        spool = self.build_folder
        self.run(f'sh "{script}" "{bindir}" "{term_root}" "{spool}"')
