#!/usr/bin/env python3
import os
from conan import ConanFile


class LibpngTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        # conan 2 的 test_package 需声明被测试的包（progress #22130 教训）
        self.requires(self.tested_reference_str)

    def test(self):
        pn = self.dependencies["libpng"]
        pn_inc = os.path.join(pn.package_folder, "include")
        pn_lib = os.path.join(pn.package_folder, "lib")
        zl = self.dependencies["zlib"]
        zl_inc = os.path.join(zl.package_folder, "include")
        zl_lib = os.path.join(zl.package_folder, "lib")
        src = os.path.join(self.source_folder, "src", "test_png.c")
        test_bin = os.path.join(self.build_folder, "test_png")
        # -I/-L 显式补齐 + -lz：libpng.a 静态库依赖 zlib
        # （karchive -lzstd -lz 同类——静态库依赖传递）
        self.run(
            f"${{CC:-clang}} ${{CFLAGS}} -o \"{test_bin}\" \"{src}\" "
            f"-I{pn_inc} -I{zl_inc} -L{pn_lib} -L{zl_lib} -lpng -lz",
            env="conanbuild",
        )
        self.run(f'"{test_bin}"', env="conanrun")
