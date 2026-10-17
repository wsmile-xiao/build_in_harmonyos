#!/usr/bin/env python3
import os
from conan import ConanFile


class LibsodiumTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        # conan 2 的 test_package 需声明被测试的包（CI #23956 报
        # doesn't declare any requirement——use self.tested_reference_str——
        # progress #22130 教训）
        self.requires(self.tested_reference_str)

    def test(self):
        so = self.dependencies["libsodium"]
        so_inc = os.path.join(so.package_folder, "include")
        so_lib = os.path.join(so.package_folder, "lib")
        src = os.path.join(self.source_folder, "src", "test_sodium.c")
        test_bin = os.path.join(self.build_folder, "test_sodium")
        self.run(
            f"${{CC:-clang}} ${{CFLAGS}} -o \"{test_bin}\" \"{src}\" "
            f"-I{so_inc} -L{so_lib} -lsodium",
            env="conanbuild",
        )
        self.run(f'"{test_bin}"', env="conanrun")
