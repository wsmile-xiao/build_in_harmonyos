#!/usr/bin/env python3
import os
from conan import ConanFile


class LibgdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        gd = self.dependencies["libgd"]
        gd_inc = os.path.join(gd.package_folder, "include")
        gd_lib = os.path.join(gd.package_folder, "lib")
        zlib = self.dependencies["zlib"]
        zlib_inc = os.path.join(zlib.package_folder, "include")
        zlib_lib = os.path.join(zlib.package_folder, "lib")
        png = self.dependencies["libpng"]
        png_inc = os.path.join(png.package_folder, "include")
        png_lib = os.path.join(png.package_folder, "lib")
        src = os.path.join(self.source_folder, "src", "test_libgd.c")
        test_bin = os.path.join(self.build_folder, "test_libgd")
        # -I/-L 显式补齐 + -lz -lpng：libgd.a 静态库依赖 zlib/libpng
        # （cattle -lffi/karchive -lzstd -lz 同类——静态库依赖传递）
        self.run(
            f"${{CC:-clang}} ${{CFLAGS}} -o \"{test_bin}\" \"{src}\" "
            f"-I{gd_inc} -I{zlib_inc} -I{png_inc} "
            f"-L{gd_lib} -L{zlib_lib} -L{png_lib} -lgd -lpng -lz",
            env="conanbuild",
        )
        self.run(f'"{test_bin}"', env="conanrun")
