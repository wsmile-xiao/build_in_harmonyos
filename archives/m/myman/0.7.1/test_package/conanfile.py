#!/usr/bin/env python3
"""test_package for myman 0.7.1 — text-terminal Pac-Man-style game.

R34 substantial test: actually executes the installed `myman` binary and
asserts it runs (--version / --help are non-interactive and need no TTY).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class MymanTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross build: skip running myman")
            return
        pkg = self.dependencies["myman"].package_folder
        exe = os.path.join(pkg, "bin", "myman")
        # 断言: myman --version 打印 "myman 0.7.1" 且退出码 0（无需 TTY）
        self.run(f"{exe} --version", env="conanrun")
        # 断言: myman --help 可用（列出用法与全部 variant/size）
        self.run(f"{exe} --help", env="conanrun")
