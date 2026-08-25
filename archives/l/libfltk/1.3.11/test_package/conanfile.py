#!/usr/bin/env python3
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["libfltk"].package_folder
        header = os.path.join(pkg, "include", "FL", "Fl.H")
        found = os.path.isfile(header)
        self.output.info(f"FL/Fl.H found: {found} ({header})")
        if not found:
            raise Exception("fltk package missing")
        script = os.path.join(self.source_folder, "src", "test_fltk.sh")
        if os.path.isfile(script):
            # 传 libx11 lib 目录：fltk-config --libs 不包含 X11 链接项，
            # 消费者程序需显式 -L<libx11>/lib -lX11 才能链接成功
            x11 = self.dependencies["libx11"]
            x11_lib = os.path.join(x11.package_folder, "lib")
            self.run(f'bash "{script}" "{pkg}" "{x11_lib}"', env="conanrun")
        self.output.info("fltk test_package PASS")
