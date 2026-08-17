#!/usr/bin/env python3
import os
from conan import ConanFile


class ProgressTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        # conan 2 的 test_package 需声明被测试的包（CI #22130 报
        # doesn't declare any requirement——use self.tested_reference_str）
        self.requires(self.tested_reference_str)

    def test(self):
        pr = self.dependencies["progress"]
        # progress 安装到 usr/bin（make install PREFIX=/usr）
        pr_bin = os.path.join(pr.package_folder, "usr", "bin", "progress")
        src = os.path.join(self.source_folder, "src", "test_progress.c")
        test_bin = os.path.join(self.build_folder, "test_progress")
        self.run(
            f"${{CC:-clang}} ${{CFLAGS}} -o \"{test_bin}\" \"{src}\"",
            env="conanbuild",
        )
        self.run(f'"{test_bin}" "{pr_bin}"', env="conanrun")
